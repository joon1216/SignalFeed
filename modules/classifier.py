"""
정치 성향 분류 모듈
BERT + TextCNN 모델을 사용하여 뉴스 기사를 진보/보수/중립으로 분류
"""

import os
import re
import json
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset as TorchDataset
from transformers import AutoTokenizer, AutoModel
from tqdm.auto import tqdm


class BertTextCNN(nn.Module):
    """BERT + TextCNN 모델"""
    def __init__(self, model_name, num_classes, num_filters=100, 
                 filter_sizes=[2, 3, 4], dropout=0.5):
        super(BertTextCNN, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        bert_dim = self.bert.config.hidden_size
        self.convs = nn.ModuleList([
            nn.Conv2d(1, num_filters, (k, bert_dim)) for k in filter_sizes
        ])
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(len(filter_sizes) * num_filters, num_classes)
        
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.zeros_(self.classifier.bias)

    def forward(self, input_ids, attention_mask=None, labels=None, **kwargs):
        bert_outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        bert_embeddings = bert_outputs.last_hidden_state
        embedded = bert_embeddings.unsqueeze(1)
        conved = [F.relu(conv(embedded)).squeeze(3) for conv in self.convs]
        pooled = [F.max_pool1d(conv, conv.shape[2]).squeeze(2) for conv in conved]
        cat = self.dropout(torch.cat(pooled, dim=1))
        logits = self.classifier(cat)
        return logits


class SimpleTorchDataset(TorchDataset):
    """간단한 PyTorch Dataset"""
    def __init__(self, encodings):
        self.encodings = encodings

    def __getitem__(self, idx):
        item = {key: val[idx].clone().detach() for key, val in self.encodings.items()}
        if 'token_type_ids' in item:
            del item['token_type_ids']
        return item

    def __len__(self):
        return len(self.encodings['input_ids'])


class PoliticalClassifier:
    """정치 성향 분류기 (pkl/bin/pt 모두 지원)"""
    
    def __init__(self, model_dir, device='cuda'):
        """
        Args:
            model_dir: 모델 파일이 있는 디렉토리
            device: 'cuda' 또는 'cpu'
        """
        self.device = device if torch.cuda.is_available() else 'cpu'
        print(f"🔧 디바이스: {self.device}")
        
        # 모델 로드
        self.model, self.tokenizer, self.config, self.reverse_label_mapping = \
            self._load_model(model_dir)
        
        # 라벨 매핑
        self.label_names = {0: 'progressive', 1: 'conservative', 2: 'neutral'}
    
    def _load_model(self, model_dir):
        """모델 로드 (자동 형식 감지)"""
        print(f"\n📂 모델 로드 중: {model_dir}")
        
        # config.json 로드
        config_path = os.path.join(model_dir, 'config.json')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"config.json이 없습니다: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # label_mapping.json 로드
        label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
        if not os.path.exists(label_mapping_path):
            raise FileNotFoundError(f"label_mapping.json이 없습니다: {label_mapping_path}")
        
        with open(label_mapping_path, 'r', encoding='utf-8') as f:
            label_mapping = json.load(f)
        
        reverse_label_mapping = {int(v): int(k) for k, v in label_mapping.items()}
        
        # 토크나이저 로드
        tokenizer_path = os.path.join(model_dir, 'tokenizer')
        if not os.path.exists(tokenizer_path):
            raise FileNotFoundError(f"tokenizer 폴더가 없습니다: {tokenizer_path}")
        
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        
        # 모델 파일 자동 감지 및 로드
        model = self._load_model_file(model_dir, config)
        model = model.to(self.device)
        model.eval()
        
        print(f"✅ 모델 로드 완료")
        print(f"   - BERT: {config['BERT_MODEL_NAME']}")
        print(f"   - 클래스: {config['NUM_CLASSES']}")
        
        return model, tokenizer, config, reverse_label_mapping
    
    def _load_model_file(self, model_dir, config):
        """모델 파일 로드 (pkl/bin/pt 자동 감지)"""
        
        # 1. pkl 파일 확인
        pkl_path = os.path.join(model_dir, 'model.pkl')
        if os.path.exists(pkl_path):
            print(f"   📦 PKL 파일 로드: {pkl_path}")
            model = torch.load(pkl_path, map_location=self.device)
            return model
        
        # 2. bin 파일 확인
        bin_path = os.path.join(model_dir, 'pytorch_model.bin')
        if os.path.exists(bin_path):
            print(f"   📦 BIN 파일 로드: {bin_path}")
            # 모델 구조 먼저 생성
            model = BertTextCNN(
                model_name=config['BERT_MODEL_NAME'],
                num_classes=config['NUM_CLASSES'],
                num_filters=config['NUM_FILTERS'],
                filter_sizes=config['FILTER_SIZES'],
                dropout=config['DROPOUT']
            )
            # 가중치 로드
            model.load_state_dict(
                torch.load(bin_path, map_location=self.device)
            )
            return model
        
        # 3. pt 파일 확인
        pt_path = os.path.join(model_dir, 'model.pt')
        if os.path.exists(pt_path):
            print(f"   📦 PT 파일 로드: {pt_path}")
            model = torch.load(pt_path, map_location=self.device)
            return model
        
        # 모델 파일을 찾지 못한 경우
        raise FileNotFoundError(
            f"모델 파일을 찾을 수 없습니다.\n"
            f"다음 중 하나를 {model_dir}에 배치하세요:\n"
            f"  - model.pkl\n"
            f"  - pytorch_model.bin\n"
            f"  - model.pt"
        )
    
    def _preprocess_text(self, text):
        """텍스트 전처리"""
        if pd.isna(text):
            return ""
        text = str(text)
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def classify_jsonl(self, input_jsonl, output_jsonl, batch_size=32):
        """
        JSONL 파일의 기사를 분류하여 결과를 JSONL로 저장
        
        Args:
            input_jsonl: 입력 JSONL 파일 (클러스터링 결과)
            output_jsonl: 출력 JSONL 파일 (분류 결과 포함)
            batch_size: 배치 크기
        """
        print("\n" + "="*70)
        print("🚀 정치 성향 분류 시작")
        print("="*70)
        
        # JSONL 로드
        print(f"\n📄 JSONL 로드: {input_jsonl}")
        articles = []
        with open(input_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                articles.append(json.loads(line))
        
        print(f"✅ {len(articles):,}개 기사 로드")
        
        # 텍스트 추출 및 전처리
        texts = []
        for article in articles:
            if self.config.get('USE_TITLE', True):
                combined = f"{article.get('title', '')} {article.get('content', '')}"
            else:
                combined = article.get('content', '')
            texts.append(self._preprocess_text(combined))
        
        # 빈 텍스트 체크
        empty_mask = [len(text) == 0 for text in texts]
        empty_count = sum(empty_mask)
        if empty_count > 0:
            print(f"⚠️ 빈 텍스트 {empty_count}개 발견")
        
        # 토큰화
        print(f"\n🔄 토큰화 중 (MAX_LENGTH={self.config['MAX_LENGTH']})...")
        encodings = self.tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=self.config['MAX_LENGTH'],
            return_tensors="pt"
        )
        
        dataset = SimpleTorchDataset(encodings)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=False
        )
        
        # 예측
        print(f"\n🔮 예측 중...")
        all_predictions = []
        all_confidences = []
        
        with torch.no_grad():
            for batch in tqdm(dataloader, desc="예측 진행"):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                logits = self.model(**batch)
                probs = F.softmax(logits, dim=-1)
                predictions = torch.argmax(logits, dim=-1)
                confidences = torch.max(probs, dim=-1).values
                
                all_predictions.extend(predictions.cpu().numpy())
                all_confidences.extend(confidences.cpu().numpy())
        
        # 결과 저장
        print(f"\n💾 결과 저장: {output_jsonl}")
        with open(output_jsonl, 'w', encoding='utf-8') as f:
            for i, (article, pred_idx, conf, is_empty) in enumerate(
                zip(articles, all_predictions, all_confidences, empty_mask)
            ):
                if is_empty:
                    # 빈 텍스트는 unknown 처리
                    article['political_stance'] = 'unknown'
                    article['stance_confidence'] = 0.0
                else:
                    pred_label = self.reverse_label_mapping[pred_idx]
                    article['political_stance'] = self.label_names.get(pred_label, 'unknown')
                    article['stance_confidence'] = float(conf)
                
                f.write(json.dumps(article, ensure_ascii=False) + '\n')
        
        # 통계 출력
        stance_counts = {}
        for pred_idx, is_empty in zip(all_predictions, empty_mask):
            if is_empty:
                label = 'unknown'
            else:
                label = self.label_names.get(self.reverse_label_mapping[pred_idx], 'unknown')
            stance_counts[label] = stance_counts.get(label, 0) + 1
        
        print("\n📊 정치성향 분포:")
        total = len(articles)
        for stance in ['progressive', 'conservative', 'neutral', 'unknown']:
            count = stance_counts.get(stance, 0)
            if count > 0:
                print(f"   {stance}: {count:,}개 ({count/total*100:.1f}%)")
        
        print("\n" + "="*70)
        print("✅ 분류 완료!")
        print("="*70)
        
        return output_jsonl


if __name__ == "__main__":
    # 테스트 코드
    import argparse
    
    parser = argparse.ArgumentParser(description='정치 성향 분류')
    parser.add_argument('--input', '-i', required=True, help='입력 JSONL 파일')
    parser.add_argument('--output', '-o', required=True, help='출력 JSONL 파일')
    parser.add_argument('--model_dir', '-m', required=True, help='모델 디렉토리')
    parser.add_argument('--batch_size', type=int, default=32, help='배치 크기')
    parser.add_argument('--device', default='cuda', help='디바이스 (cuda/cpu)')
    
    args = parser.parse_args()
    
    classifier = PoliticalClassifier(
        model_dir=args.model_dir,
        device=args.device
    )
    
    classifier.classify_jsonl(
        input_jsonl=args.input,
        output_jsonl=args.output,
        batch_size=args.batch_size
    )

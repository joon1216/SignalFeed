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
from safetensors.torch import load_file as safetensors_load
from tqdm.auto import tqdm


class BertTextCNN(nn.Module):
    """BERT + TextCNN 모델 (기본 버전)"""
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


class BertTextCNNAttention(nn.Module):
    """BERT + TextCNN + Attention 모델 (개선 버전)"""
    def __init__(self, model_name, num_classes, num_filters=256, 
                 filter_sizes=[2, 3, 4], dropout=0.3, attention_heads=8):
        super(BertTextCNNAttention, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        bert_dim = self.bert.config.hidden_size
        
        # TextCNN 레이어들
        self.convs = nn.ModuleList([
            nn.Conv2d(1, num_filters, (k, bert_dim)) for k in filter_sizes
        ])
        
        # 추가 conv 레이어 (convs.3)
        if len(filter_sizes) == 3:
            self.convs.append(nn.Conv2d(1, num_filters, (5, bert_dim)))
        
        # Attention 레이어
        self.attention = nn.MultiheadAttention(
            embed_dim=num_filters * len(self.convs),
            num_heads=attention_heads,
            batch_first=True
        )
        
        # Layer Normalization
        self.layer_norm = nn.LayerNorm(num_filters * len(self.convs))
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # 최종 분류 레이어 (fc)
        self.fc = nn.Linear(num_filters * len(self.convs), num_classes)
        
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, input_ids, attention_mask=None, labels=None, **kwargs):
        bert_outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        bert_embeddings = bert_outputs.last_hidden_state
        embedded = bert_embeddings.unsqueeze(1)
        
        # TextCNN 적용
        conved = [F.relu(conv(embedded)).squeeze(3) for conv in self.convs]
        pooled = [F.max_pool1d(conv, conv.shape[2]).squeeze(2) for conv in conved]
        cat = torch.cat(pooled, dim=1)  # [batch, num_filters * num_convs]
        
        # Attention 적용 (배치 차원 추가)
        cat_expanded = cat.unsqueeze(1)  # [batch, 1, num_filters * num_convs]
        attn_out, _ = self.attention(cat_expanded, cat_expanded, cat_expanded)
        attn_out = attn_out.squeeze(1)  # [batch, num_filters * num_convs]
        
        # Layer Norm + Dropout
        attn_out = self.layer_norm(attn_out)
        attn_out = self.dropout(attn_out)
        
        # 최종 분류
        logits = self.fc(attn_out)
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
        
        # config.json 형식 정규화 (새 형식과 기존 형식 모두 지원)
        config = self._normalize_config(config)
        
        # label_mapping.json 로드 또는 자동 생성
        label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
        if os.path.exists(label_mapping_path):
            with open(label_mapping_path, 'r', encoding='utf-8') as f:
                label_mapping = json.load(f)
        else:
            # label_mapping.json이 없으면 config.json의 label_names로부터 생성
            print(f"   ⚠️ label_mapping.json이 없습니다. config.json의 label_names로부터 생성합니다.")
            if 'label_names' in config:
                # 새 형식: label_names가 {0: "진보", 1: "중립", 2: "보수"} 형태
                label_mapping = {str(k): k for k in config['label_names'].keys()}
            else:
                # 기본값: 3개 클래스 (진보, 중립, 보수)
                label_mapping = {"0": 0, "1": 1, "2": 2}
            # 파일로 저장
            with open(label_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(label_mapping, f, ensure_ascii=False, indent=2)
            print(f"   ✅ label_mapping.json 생성 완료")
        
        reverse_label_mapping = {int(v): int(k) for k, v in label_mapping.items()}
        
        # 토크나이저 로드 (tokenizer 폴더 또는 루트에서)
        tokenizer_path = os.path.join(model_dir, 'tokenizer')
        if not os.path.exists(tokenizer_path):
            # tokenizer 폴더가 없으면 루트에서 직접 로드 시도
            tokenizer_path = model_dir
            print(f"   ⚠️ tokenizer 폴더가 없습니다. 루트에서 로드 시도합니다.")
        
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        
        # 모델 파일 자동 감지 및 로드
        model = self._load_model_file(model_dir, config)
        model = model.to(self.device)
        model.eval()
        
        print(f"✅ 모델 로드 완료")
        print(f"   - BERT: {config['BERT_MODEL_NAME']}")
        print(f"   - 클래스: {config['NUM_CLASSES']}")
        
        return model, tokenizer, config, reverse_label_mapping
    
    def _normalize_config(self, config):
        """config.json 형식을 정규화 (새 형식과 기존 형식 모두 지원)"""
        normalized = config.copy()
        
        # 새 형식 -> 기존 형식 변환
        if 'model_name' in config:
            normalized['BERT_MODEL_NAME'] = config['model_name']
        if 'num_classes' in config:
            normalized['NUM_CLASSES'] = config['num_classes']
        if 'max_length' in config:
            normalized['MAX_LENGTH'] = config['max_length']
        if 'dropout' in config:
            normalized['DROPOUT'] = config['dropout']
        if 'num_filters' in config:
            normalized['NUM_FILTERS'] = config['num_filters']
        if 'filter_sizes' in config:
            normalized['FILTER_SIZES'] = config['filter_sizes']
        else:
            # 기본값 설정
            if 'NUM_FILTERS' not in normalized:
                normalized['NUM_FILTERS'] = 100
            if 'FILTER_SIZES' not in normalized:
                normalized['FILTER_SIZES'] = [2, 3, 4]
        
        # Attention 관련 설정
        if 'attention_heads' in config:
            normalized['ATTENTION_HEADS'] = config['attention_heads']
        
        # USE_TITLE 기본값
        if 'USE_TITLE' not in normalized:
            normalized['USE_TITLE'] = True
        
        return normalized
    
    def _detect_model_type(self, state_dict):
        """state_dict를 분석하여 모델 타입 감지"""
        has_attention = any('attention' in key for key in state_dict.keys())
        has_fc = 'fc.weight' in state_dict or 'fc.bias' in state_dict
        has_classifier = 'classifier.weight' in state_dict or 'classifier.bias' in state_dict
        has_convs3 = 'convs.3.weight' in state_dict or 'convs.3.bias' in state_dict
        
        if has_attention or has_fc or has_convs3:
            return 'attention'
        else:
            return 'basic'
    
    def _convert_conv1d_to_conv2d(self, state_dict):
        """Conv1d weight를 Conv2d weight로 변환"""
        new_state_dict = {}
        for key, value in state_dict.items():
            if 'convs' in key and 'weight' in key and len(value.shape) == 3:
                # Conv1d shape: (out_channels, in_channels, kernel_size)
                # Conv2d shape: (out_channels, 1, kernel_size, in_channels)
                out_ch, in_ch, kernel_size = value.shape
                new_value = value.unsqueeze(1).permute(0, 1, 3, 2)  # (out_ch, 1, in_ch, kernel_size)
                new_state_dict[key] = new_value
            else:
                new_state_dict[key] = value
        return new_state_dict
    
    def _load_model_file(self, model_dir, config):
        """모델 파일 로드 (pkl/bin/pt/safetensors 자동 감지)"""
        
        # 1. pkl 파일 확인
        pkl_path = os.path.join(model_dir, 'model.pkl')
        if os.path.exists(pkl_path):
            print(f"   📦 PKL 파일 로드: {pkl_path}")
            model = torch.load(pkl_path, map_location=self.device)
            return model
        
        # 2. safetensors 파일 확인 (새 형식)
        safetensors_path = os.path.join(model_dir, 'model.safetensors')
        if os.path.exists(safetensors_path):
            print(f"   📦 Safetensors 파일 로드: {safetensors_path}")
            # 가중치 먼저 로드하여 모델 타입 감지
            state_dict = safetensors_load(safetensors_path)
            model_type = self._detect_model_type(state_dict)
            
            # Conv1d -> Conv2d 변환이 필요한지 확인
            needs_conversion = any('convs' in k and len(state_dict[k].shape) == 3 for k in state_dict.keys())
            if needs_conversion:
                print(f"   🔄 Conv1d -> Conv2d 변환 중...")
                state_dict = self._convert_conv1d_to_conv2d(state_dict)
            
            if model_type == 'attention':
                print(f"   🔍 Attention 모델 감지")
                # Attention 모델 생성
                model = BertTextCNNAttention(
                    model_name=config['BERT_MODEL_NAME'],
                    num_classes=config['NUM_CLASSES'],
                    num_filters=config.get('NUM_FILTERS', 256),
                    filter_sizes=config.get('FILTER_SIZES', [2, 3, 4]),
                    dropout=config['DROPOUT'],
                    attention_heads=config.get('ATTENTION_HEADS', 8)
                )
            else:
                print(f"   🔍 기본 TextCNN 모델 감지")
                # 기본 TextCNN 모델 생성
                model = BertTextCNN(
                    model_name=config['BERT_MODEL_NAME'],
                    num_classes=config['NUM_CLASSES'],
                    num_filters=config.get('NUM_FILTERS', 100),
                    filter_sizes=config.get('FILTER_SIZES', [2, 3, 4]),
                    dropout=config['DROPOUT']
                )
            
            # 가중치 로드
            model.load_state_dict(state_dict)
            return model
        
        # 3. bin 파일 확인
        bin_path = os.path.join(model_dir, 'pytorch_model.bin')
        if os.path.exists(bin_path):
            print(f"   📦 BIN 파일 로드: {bin_path}")
            # 가중치 먼저 로드하여 모델 타입 감지
            state_dict = torch.load(bin_path, map_location=self.device)
            model_type = self._detect_model_type(state_dict)
            
            if model_type == 'attention':
                print(f"   🔍 Attention 모델 감지")
                model = BertTextCNNAttention(
                    model_name=config['BERT_MODEL_NAME'],
                    num_classes=config['NUM_CLASSES'],
                    num_filters=config.get('NUM_FILTERS', 256),
                    filter_sizes=config.get('FILTER_SIZES', [2, 3, 4]),
                    dropout=config['DROPOUT'],
                    attention_heads=config.get('ATTENTION_HEADS', 8)
                )
            else:
                print(f"   🔍 기본 TextCNN 모델 감지")
                model = BertTextCNN(
                    model_name=config['BERT_MODEL_NAME'],
                    num_classes=config['NUM_CLASSES'],
                    num_filters=config.get('NUM_FILTERS', 100),
                    filter_sizes=config.get('FILTER_SIZES', [2, 3, 4]),
                    dropout=config['DROPOUT']
                )
            
            model.load_state_dict(state_dict)
            return model
        
        # 4. pt 파일 확인
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
            f"  - model.safetensors\n"
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

"""
YouTube Shorts 생성 모듈 (매크로 차트 사이버펑크 스타일)

입력: scripts.json의 클러스터 스크립트
출력: data/5_shorts/cluster_{id}.mp4 (38-42초, 1080x1920)

기술 스택:
- yfinance: 나스닥, KOSPI, 원달러 환율 데이터
- mplcyberpunk: 사이버펑크 차트 스타일
- gTTS: 한국어 TTS
- moviepy: 비디오 합성
- FFmpeg: 자막 렌더링
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import mplcyberpunk
import yfinance as yf
import numpy as np
from gtts import gTTS
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShortsGenerator:
    """
    매크로 차트 사이버펑크 릴스 생성기
    """

    def __init__(self):
        self.output_dir = 'data/5_shorts'
        self.temp_dir = 'data/temp'
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # 차트 설정
        self.width = 1080
        self.height = 1920
        self.dpi = 100
        self.fps = 24

        # 색상 팔레트
        self.colors = {
            'bg': '#212946',
            'nasdaq_up': '#00ff41',  # 매트릭스 그린
            'nasdaq_down': '#08F7FE',  # 시안
            'kospi_up': '#00ff41',
            'kospi_down': '#08F7FE',
            'brand': '#00C853',
            'text': '#FFFFFF'
        }

    def generate_tts(self, text: str, output_path: str) -> float:
        """
        gTTS로 한국어 TTS 생성

        Args:
            text: 나레이션 텍스트
            output_path: 출력 mp3 파일 경로

        Returns:
            오디오 길이 (초)
        """
        logger.info(f"TTS 생성 중: {len(text)} 글자")

        tts = gTTS(text=text, lang='ko', slow=False)
        tts.save(output_path)

        # 오디오 길이 계산 (대략 150글자/분)
        duration = len(text) / 150 * 60
        logger.info(f"TTS 생성 완료: {duration:.1f}초")

        return duration

    def _fetch_market_data(self, ticker: str, days: int = 30) -> Optional[np.ndarray]:
        """
        yfinance로 시장 데이터 가져오기

        Args:
            ticker: 티커 심볼 (^IXIC, ^KS11, KRW=X)
            days: 데이터 일수

        Returns:
            종가 데이터 (numpy array)
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            data = yf.download(
                ticker,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                progress=False
            )

            if data.empty:
                logger.warning(f"데이터 없음: {ticker}")
                return None

            close_prices = data['Close'].values
            logger.info(f"{ticker} 데이터: {len(close_prices)}일")
            return close_prices

        except Exception as e:
            logger.error(f"{ticker} 데이터 가져오기 실패: {e}")
            return None

    def generate_chart_image(
        self,
        cluster_data: Dict,
        output_path: str
    ) -> bool:
        """
        mplcyberpunk 사이버펑크 정적 차트 이미지 생성

        Args:
            cluster_data: 클러스터 스크립트 데이터
            output_path: 출력 PNG 파일 경로

        Returns:
            성공 여부
        """
        logger.info("차트 이미지 생성 중...")

        # 시장 데이터 가져오기
        nasdaq_data = self._fetch_market_data('^IXIC', days=30)
        kospi_data = self._fetch_market_data('^KS11', days=30)

        if nasdaq_data is None or kospi_data is None:
            logger.error("시장 데이터 가져오기 실패")
            return False

        # 데이터 정규화 (0~100)
        nasdaq_normalized = (nasdaq_data - nasdaq_data.min()) / (nasdaq_data.max() - nasdaq_data.min()) * 100
        kospi_normalized = (kospi_data - kospi_data.min()) / (kospi_data.max() - kospi_data.min()) * 100

        # 사이버펑크 스타일 적용
        plt.style.use('cyberpunk')

        # Figure 설정 (9:16 세로)
        fig = plt.figure(
            figsize=(self.width / self.dpi, self.height / self.dpi),
            dpi=self.dpi
        )
        fig.patch.set_facecolor(self.colors['bg'])

        # 서브플롯 (상단 60%, 하단 40%)
        ax1 = plt.subplot2grid((10, 1), (0, 0), rowspan=6, fig=fig)
        ax2 = plt.subplot2grid((10, 1), (6, 0), rowspan=4, fig=fig)

        for ax in [ax1, ax2]:
            ax.set_facecolor(self.colors['bg'])
            ax.grid(True, alpha=0.2, color='#FFFFFF', linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#FFFFFF')
            ax.spines['bottom'].set_color('#FFFFFF')
            ax.tick_params(colors='#FFFFFF', labelsize=10)

        # 제목 설정
        fig.suptitle(
            'SIGNALFEED',
            fontsize=24,
            color=self.colors['brand'],
            weight='bold',
            x=0.5,
            y=0.98
        )

        ax1.set_title(
            f'NASDAQ ({len(nasdaq_data)} days)',
            fontsize=16,
            color='#00ff41',
            pad=20
        )
        ax2.set_title(
            f'KOSPI ({len(kospi_data)} days)',
            fontsize=14,
            color='#08F7FE',
            pad=10
        )

        # 차트 그리기
        x_nasdaq = np.arange(len(nasdaq_normalized))
        x_kospi = np.arange(len(kospi_normalized))

        ax1.plot(x_nasdaq, nasdaq_normalized, linewidth=3, color='#00ff41')
        ax2.plot(x_kospi, kospi_normalized, linewidth=3, color='#08F7FE')

        # 네온 효과 적용
        try:
            mplcyberpunk.make_lines_glow(ax1)
            mplcyberpunk.make_lines_glow(ax2)
            mplcyberpunk.add_underglow(ax1)
            mplcyberpunk.add_underglow(ax2)
        except Exception as e:
            logger.warning(f"Glow 효과 적용 실패: {e}")

        # 축 범위 설정
        ax1.set_xlim(0, len(nasdaq_normalized))
        ax1.set_ylim(0, 110)
        ax2.set_xlim(0, len(kospi_normalized))
        ax2.set_ylim(0, 110)

        # PNG 저장
        logger.info(f"차트 이미지 저장 중: {output_path}")

        try:
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, facecolor=self.colors['bg'])
            logger.info("차트 이미지 저장 완료")
            plt.close(fig)
            return True
        except Exception as e:
            logger.error(f"이미지 저장 실패: {e}")
            plt.close(fig)
            return False

    def chart_to_video(
        self,
        chart_png: str,
        output_path: str,
        duration: float
    ) -> bool:
        """
        정적 차트 이미지를 비디오로 변환 (MoviePy)

        Args:
            chart_png: 차트 PNG 경로
            output_path: 출력 MP4 경로
            duration: 비디오 길이 (초)

        Returns:
            성공 여부
        """
        try:
            from moviepy import ImageClip

            logger.info(f"차트 이미지 → 비디오 변환 중: {duration:.1f}초")

            # 이미지 클립 생성
            clip = ImageClip(chart_png).with_duration(duration)

            # MP4 저장
            clip.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                preset='ultrafast',
                threads=4,
                logger=None
            )

            clip.close()
            logger.info("차트 비디오 변환 완료")
            return True

        except Exception as e:
            logger.error(f"비디오 변환 실패: {e}")
            return False

    def _build_tts_script(self, script_data: Dict) -> str:
        """
        TTS 스크립트 자동 생성 (Gemini 없이)

        Args:
            script_data: 클러스터 스크립트

        Returns:
            TTS 텍스트
        """
        hook = script_data.get('hook_title', '').replace('\n', ' ')
        one_line = script_data.get('one_line', '')

        return f"""
AI가 오늘의 글로벌 경제 신호를 분석했습니다.
{hook}.
{one_line}.
데이터는 감정이 없습니다.
매일 아침 가장 냉철한 AI 시그널을 받아보시려면 구독하세요.
""".strip()

    def compose_video(
        self,
        chart_mp4: str,
        audio_mp3: str,
        output_path: str
    ) -> bool:
        """
        MoviePy로 차트 + TTS 합성

        Args:
            chart_mp4: 차트 영상 경로
            audio_mp3: TTS 오디오 경로
            output_path: 최종 출력 경로

        Returns:
            성공 여부
        """
        logger.info("비디오 합성 중...")

        try:
            # 차트 영상 로드
            video = VideoFileClip(chart_mp4)

            # TTS 오디오 로드
            audio = AudioFileClip(audio_mp3)

            # 오디오 길이에 맞춰 영상 길이 조정
            if video.duration < audio.duration:
                # 영상이 짧으면 마지막 프레임 freeze
                video = video.set_duration(audio.duration)
            else:
                # 영상이 길면 자르기
                video = video.subclipped(0, audio.duration)

            # 오디오 합성
            video = video.with_audio(audio)

            # 최종 저장
            logger.info(f"최종 영상 저장 중: {output_path}")
            video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                threads=4,
                logger=None  # MoviePy 로그 숨기기
            )

            # 리소스 정리
            video.close()
            audio.close()

            logger.info("비디오 합성 완료")
            return True

        except Exception as e:
            logger.error(f"비디오 합성 실패: {e}")
            return False

    def generate(self, script_data: Dict) -> Optional[str]:
        """
        메인 진입점: 클러스터 스크립트 → 릴스 영상 생성

        Args:
            script_data: scripts.json의 클러스터 데이터

        Returns:
            생성된 영상 경로 (실패 시 None)
        """
        cluster_id = script_data.get('cluster_id', '0')
        logger.info(f"=== Cluster {cluster_id} 릴스 생성 시작 ===")

        # 파일 경로 설정
        tts_path = os.path.join(self.temp_dir, f'tts_{cluster_id}.mp3')
        chart_path = os.path.join(self.temp_dir, f'chart_{cluster_id}.mp4')
        output_path = os.path.join(self.output_dir, f'cluster_{cluster_id}.mp4')

        try:
            # Step 1: TTS 생성
            tts_script = self._build_tts_script(script_data)
            logger.info(f"TTS 스크립트: {tts_script[:100]}...")

            duration = self.generate_tts(tts_script, tts_path)

            # Step 2: 차트 이미지 생성
            chart_png = os.path.join(self.temp_dir, f'chart_{cluster_id}.png')
            success = self.generate_chart_image(script_data, chart_png)

            if not success:
                logger.error("차트 이미지 생성 실패")
                return None

            # Step 3: 차트 이미지 → 비디오
            success = self.chart_to_video(chart_png, chart_path, duration)

            if not success:
                logger.error("차트 비디오 변환 실패")
                return None

            # Step 4: 비디오 합성
            success = self.compose_video(chart_path, tts_path, output_path)

            if not success:
                logger.error("비디오 합성 실패")
                return None

            logger.info(f"✅ Cluster {cluster_id} 릴스 생성 완료: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Cluster {cluster_id} 릴스 생성 실패: {e}")
            return None

        finally:
            # 임시 파일 정리
            for temp_file in [tts_path, chart_path]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug(f"임시 파일 삭제: {temp_file}")
                    except Exception as e:
                        logger.warning(f"임시 파일 삭제 실패: {temp_file} - {e}")


def main():
    """
    테스트 실행
    """
    import json

    # scripts.json 로드
    scripts_path = 'data/3_generated/scripts.json'

    if not os.path.exists(scripts_path):
        logger.error(f"scripts.json 없음: {scripts_path}")
        return

    with open(scripts_path, 'r', encoding='utf-8') as f:
        scripts = json.load(f)

    if not scripts:
        logger.error("scripts.json이 비어있음")
        return

    # 생성기 초기화
    generator = ShortsGenerator()

    # 첫 2개 클러스터만 테스트
    for script in scripts[:2]:
        output_path = generator.generate(script)

        if output_path:
            logger.info(f"✅ 생성 완료: {output_path}")
        else:
            logger.error(f"❌ 생성 실패: cluster {script.get('cluster_id')}")


if __name__ == '__main__':
    main()

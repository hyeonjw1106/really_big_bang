import asyncio
from app.core.db import engine, SessionLocal
from app.db.models import Base, Epoch, Annotation, Element, CosmicEvent

async def run():
    # 테이블 없으면 생성 (알레빅 이후에도 안전망)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        # Epoch
        bb = Epoch(name="Big Bang", start_norm=0.00, end_norm=0.05, description="초기 급팽창 및 기본 입자 생성")
        rc = Epoch(name="Recombination", start_norm=0.35, end_norm=0.40, description="우주 투명화, CMB 형성")
        s.add_all([bb, rc])
        await s.flush()  # bb.id, rc.id 확보

        # Annotation
        s.add_all([
            Annotation(epoch_id=bb.id, title="Inflation", content="인플레이션 가설", time_mark=0.02),
            Annotation(epoch_id=rc.id, title="CMB", content="우주 배경 복사", time_mark=0.37),
        ])

        # Element
        s.add_all([
            Element(name="Up Quark", type="quark", description="전하 +2/3", charge_range="+2/3", mass_gev=0.0023, genesis_time="10^-12 s"),
            Element(name="Hydrogen", type="atom", description="가장 풍부한 원자", charge_range="0", mass_gev=0.938, genesis_time="~380,000 years"),
        ])

        # CosmicEvent (큰 스케일 구간용)
        s.add_all([
            CosmicEvent(title="쿼크 생성", description="쿼크-글루온 플라즈마 형성", category="particles", time_norm=0.00001, epoch_id=bb.id, media_url=None),
            CosmicEvent(title="양성자/중성자 결합", description="핵합성 시작", category="nucleosynthesis", time_norm=0.00002, epoch_id=bb.id, media_url=None),
            CosmicEvent(title="원자 형성", description="전자 포획으로 중성 원자 생성", category="atoms", time_norm=0.02, epoch_id=rc.id, media_url=None),
            CosmicEvent(title="CMB 방출", description="재결합 이후 우주 투명화", category="cosmic_microwave_background", time_norm=0.037, epoch_id=rc.id, media_url=None),
            CosmicEvent(title="별/은하 형성 시작", description="중력 붕괴로 최초 별과 은하 생성", category="structure", time_norm=0.2, epoch_id=rc.id, media_url=None),
        ])

        await s.commit()

if __name__ == "__main__":
    asyncio.run(run())

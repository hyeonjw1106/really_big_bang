import asyncio
from app.core.db import engine, SessionLocal
from app.db.models import Base, Epoch, Annotation, Element

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

        await s.commit()

if __name__ == "__main__":
    asyncio.run(run())
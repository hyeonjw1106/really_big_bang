import asyncio
from sqlalchemy import select, func
from app.core.db import engine, SessionLocal
from app.core.storage import ensure_subdir
from app.db.models import Base, Epoch, Annotation, Element, CosmicEvent, SceneFile

async def run():
    # 테이블 없으면 생성 (알레빅 이후에도 안전망)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        # 기본 블렌더 씬 플레이스홀더 생성 (없을 경우)
        scenes_dir = ensure_subdir("scenes")
        placeholder_path = scenes_dir / "placeholder.blend"
        if not placeholder_path.exists():
            placeholder_path.write_text("placeholder blend file (dummy)")

        placeholder_scene = (await s.execute(select(SceneFile).where(SceneFile.name == "Placeholder Scene"))).scalar_one_or_none()
        if not placeholder_scene:
            placeholder_scene = SceneFile(
                name="Placeholder Scene",
                original_name="placeholder.blend",
                file_path=str(placeholder_path),
                file_size=placeholder_path.stat().st_size,
            )
            s.add(placeholder_scene)
            await s.flush()

        # Epoch
        epoch_count = await s.scalar(select(func.count()).select_from(Epoch))
        if epoch_count == 0:
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
        element_count = await s.scalar(select(func.count()).select_from(Element))
        if element_count == 0:
            s.add_all([
                Element(name="Up Quark", type="quark", description="전하 +2/3", charge_range="+2/3", mass_gev=0.0023, genesis_time="10^-12 s"),
                Element(name="Hydrogen", type="atom", description="가장 풍부한 원자", charge_range="0", mass_gev=0.938, genesis_time="~380,000 years"),
            ])

        # CosmicEvent (큰 스케일 구간용) - 타이틀 기반 업서트
        if epoch_count == 0:
            bb_id, rc_id = bb.id, rc.id
        else:
            bb_id = (await s.execute(select(Epoch.id).where(Epoch.name == "Big Bang"))).scalar_one()
            rc_id = (await s.execute(select(Epoch.id).where(Epoch.name == "Recombination"))).scalar_one()

        event_defs = [
            dict(
                title="전자·쿼크 생성",
                description="전자와 쿼크 같은 최초의 입자가 만들어진다.",
                category="particles",
                time_range="10^-12s ~ 10^-6s",
                time_norm=0.00001,
                epoch_id=bb_id,
            ),
            dict(
                title="양성자·중성자 형성",
                description="쿼크가 결합하여 양성자와 중성자가 만들어진다.",
                category="nucleosynthesis",
                time_range="10^-6s ~ 1s",
                time_norm=0.00002,
                epoch_id=bb_id,
            ),
            dict(
                title="수소 원자핵 형성",
                description="양성자와 중성자가 결합하여 수소 원자핵이 만들어진다.",
                category="hydrogen_nucleus",
                time_range="1s ~ 수분",
                time_norm=0.0001,
                epoch_id=bb_id,
            ),
            dict(
                title="헬륨 원자핵 형성",
                description="양성자와 중성자가 결합하여 헬륨 원자핵이 만들어진다.",
                category="helium_nucleus",
                time_range="수분 ~ 수십분",
                time_norm=0.0002,
                epoch_id=bb_id,
            ),
            dict(
                title="수소 원자",
                description="원자핵과 전자가 결합하여 수소 원자가 만들어진다.",
                category="hydrogen_atom",
                time_range="수십만 년",
                time_norm=0.02,
                epoch_id=rc_id,
            ),
            dict(
                title="헬륨 원자",
                description="원자핵과 전자가 결합하여 헬륨 원자가 만들어진다.",
                category="helium_atom",
                time_range="수십만 년",
                time_norm=0.025,
                epoch_id=rc_id,
            ),
        ]

        for ed in event_defs:
            existing = (await s.execute(select(CosmicEvent).where(CosmicEvent.title == ed["title"]))).scalar_one_or_none()
            if existing:
                existing.description = ed["description"]
                existing.category = ed["category"]
                existing.time_range = ed["time_range"]
                existing.time_norm = ed["time_norm"]
                existing.epoch_id = ed["epoch_id"]
                existing.default_scene_id = placeholder_scene.id
            else:
                s.add(
                    CosmicEvent(
                        title=ed["title"],
                        description=ed["description"],
                        category=ed["category"],
                        time_range=ed["time_range"],
                        time_norm=ed["time_norm"],
                        epoch_id=ed["epoch_id"],
                        media_url=None,
                        default_scene_id=placeholder_scene.id,
                    )
                )

        await s.commit()

if __name__ == "__main__":
    asyncio.run(run())

import "./App.css";
import { useEffect, useMemo, useRef, useState } from "react";
import Viewer from "./components/Viewer";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function MainPage() {
    const [events, setEvents] = useState([]);
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [job, setJob] = useState(null);
    const [jobMessage, setJobMessage] = useState("");
    const [renderUrl, setRenderUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const pollTimer = useRef(null);

    useEffect(() => {
        const load = async () => {
            try {
                const [evRes] = await Promise.all([
                    fetch(`${API_BASE}/events`),
                ]);
                const evData = await evRes.json();
                setEvents(evData);
                if (evData.length) setSelectedEvent(evData[0]);
            } catch (err) {
                console.error(err);
            }
        };
        load();
        return () => {
            if (pollTimer.current) clearTimeout(pollTimer.current);
        };
    }, []);

    useEffect(() => {
        return () => {
            if (renderUrl) URL.revokeObjectURL(renderUrl);
        };
    }, [renderUrl]);

    const currentTimeLabel = useMemo(() => {
        if (!selectedEvent) return "이벤트를 선택하세요";
        const n = (selectedEvent.time_norm * 100).toFixed(3);
        return `${selectedEvent.title} · 정규화 ${n}%`;
    }, [selectedEvent]);

    const triggerRender = async () => {
        if (!selectedEvent) {
            alert("렌더할 이벤트를 선택하세요.");
            return;
        }
        setLoading(true);
        setRenderUrl("");
        setJobMessage("렌더 요청 중...");
        try {
            const res = await fetch(`${API_BASE}/events/${selectedEvent.id}/render`, {
                method: "POST",
            });
            if (!res.ok) throw new Error("렌더 요청 실패");
            const data = await res.json();
            setJob(data);
            setJobMessage("큐에 등록되었습니다. 처리 중...");
            pollJob(data.id);
        } catch (err) {
            console.error(err);
            setJobMessage("렌더 요청 실패");
            setLoading(false);
        }
    };

    const pollJob = async (jobId) => {
        const poll = async () => {
            try {
                const res = await fetch(`${API_BASE}/renders/${jobId}`);
                if (!res.ok) throw new Error("상태 조회 실패");
                const data = await res.json();
                setJob(data);
                setJobMessage(data.message || data.status);
                if (data.status === "done") {
                    await fetchRenderFile(jobId);
                    setLoading(false);
                    return;
                }
                if (data.status === "failed") {
                    setLoading(false);
                    return;
                }
                pollTimer.current = setTimeout(poll, 1200);
            } catch (err) {
                console.error(err);
                setJobMessage("상태 확인 실패");
                setLoading(false);
            }
        };
        await poll();
    };

    const fetchRenderFile = async (jobId) => {
        try {
            const res = await fetch(`${API_BASE}/renders/${jobId}/file`);
            if (!res.ok) throw new Error("결과를 가져오지 못했습니다.");
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            setRenderUrl((prev) => {
                if (prev) URL.revokeObjectURL(prev);
                return url;
            });
            setJobMessage("렌더 완료");
        } catch (err) {
            console.error(err);
            setJobMessage("결과를 가져오지 못했습니다.");
        }
    };

    return (
        <div className="page-shell">
            <header className="hero">
                <div>
                    <p className="eyebrow">Time Cosmos</p>
                    <h1>코스믹 이벤트를 선택하고 렌더를 실행하세요</h1>
                    <p className="muted">
                        쿼크 생성부터 원자, 은하 형성까지 주요 시점을 선택해 서버에서 3D 모델(.glb)을 생성하고 인터랙티브 뷰어로 확인합니다.
                    </p>
                    <div className="chip-row">
                        <span className="chip">{currentTimeLabel}</span>
                        {job && <span className="chip subtle">Job #{job.id} · {job.status}</span>}
                    </div>
                </div>
                <button className="primary" onClick={triggerRender} disabled={loading}>
                    {loading ? "처리 중..." : "3D 모델 생성"}
                </button>
            </header>

            <main className="layout">
                <section className="panel render">
                    <div className="panel-head">
                        <div>
                            <p className="label">렌더 결과</p>
                            <h3>{renderUrl ? "인터랙티브 3D 모델" : "3D 모델 대기 중"}</h3>
                        </div>
                        <div className="status">{jobMessage || "결과가 여기 표시됩니다."}</div>
                    </div>
                    <div className="render-frame">
                        {loading && !renderUrl && <div className="render-overlay">모델 생성 중...</div>}
                        {renderUrl ? (
                            <Viewer url={renderUrl} />
                        ) : (
                            <div className="render-placeholder">
                                <p>이벤트를 선택하고 렌더를 실행하세요.</p>
                                <p className="muted">완료 시 여기에 3D 모델이 표시됩니다.</p>
                            </div>
                        )}
                    </div>
                </section>

                <section className="panel events">
                    <div className="panel-head">
                        <div>
                            <p className="label">코스믹 이벤트</p>
                            <h3>큰 단계 타임라인</h3>
                        </div>
                    </div>
                    <div className="event-list">
                        {events.map((ev) => (
                            <button
                                key={ev.id}
                                className={`event-card ${selectedEvent?.id === ev.id ? "active" : ""}`}
                                onClick={() => setSelectedEvent(ev)}
                            >
                                <div className="event-title">{ev.title}</div>
                                <div className="event-meta">
                                    {ev.category || "unknown"} · time_norm {ev.time_norm}
                                </div>
                                <div className="event-desc">{ev.time_range || "시간대 정보 없음"}</div>
                                <div className="event-desc">{ev.description || "설명 없음"}</div>
                            </button>
                        ))}
                        {events.length === 0 && <p className="muted">시드 데이터를 로드하거나 이벤트를 추가하세요.</p>}
                    </div>
                </section>

            </main>
        </div>
    );
}

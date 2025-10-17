import "./App.css";
import { useState } from "react";

export default function MainPage() {
    const [showModal, setShowModal] = useState(false);
    const [year, setYear] = useState("");
    const [minute, setMinute] = useState("");
    const [displayText, setDisplayText] = useState("");

    const handleApply = () => {
        // 입력값이 없을 경우 경고
        if (!year && !minute) {
            alert("년 또는 분 중 하나 이상을 입력해주세요!");
            return;
        }

        // 렌더링할 문장 생성
        const text = `${year ? `${year}년 ` : ""}${minute ? `${minute}분` : ""} 후의 우주`;
        setDisplayText(text);
        setShowModal(false); // 모달 닫기
    };

    return (
        <>
            <div className="model-render-div">
                <h1>{displayText}</h1>
            </div>

            <div className="underbar">
                <button
                    className="time-insert"
                    onClick={() => setShowModal(true)}
                >
                    구체 시간 입력하기
                </button>

                {showModal && (
                    <div className="time-insert-modal">
                        <h3>빅뱅이 일어난 후 얼마 후의 우주를 보고 싶나요?</h3>

                        <div className="input-group">
                            <input
                                type="text"
                                placeholder="년"
                                className="time-insert-modal-year"
                                value={year}
                                onChange={(e) => setYear(e.target.value)}
                            />
                            <input
                                type="text"
                                placeholder="분"
                                className="time-insert-modal-minute"
                                value={minute}
                                onChange={(e) => setMinute(e.target.value)}
                            />
                        </div>

                        <div className="button-group">
                            <button
                                className="accept-button"
                                onClick={handleApply}
                            >
                                적용
                            </button>
                            <button
                                className="cancle-button"
                                onClick={() => setShowModal(false)}
                            >
                                취소
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}

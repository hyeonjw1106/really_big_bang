import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import "./App.css";
import titleSpace from "./assets/title-space.png";
import MainPage from "./MainPage";

function StartPage() {
  const [status, setStatus] = useState("Loading...");
  const navigate = useNavigate();

  useEffect(() => {
    fetch("http://127.0.0.1:8000/health")
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Error"));
  }, []);

  return (
    <div className="start-div">
      <img src={titleSpace} className="title-img" alt="title space" />
      <h1 className="cosmic-viewer">Time Cosmos</h1>
      <button className="start-button" onClick={() => navigate("/main")}>
        여행 떠나기
      </button>
      <p>Status: {status}</p>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<StartPage />} />
        <Route path="/main" element={<MainPage />} />
      </Routes>
    </Router>
  );
}


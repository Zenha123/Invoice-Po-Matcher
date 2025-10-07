


import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import WelcomePage from "./pages/WelcomePage";
import UploadPage from "./pages/UploadPage";
// import ResultPage from "./pages/ResultPage";
// import Header from "./components/Header";
import POReviewPage from "./pages/dashboard";

// import "./styles/main.css";



function App() {
  return (
    <Router>
      
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        {/* <Route path="/results" element={<ResultPage />} /> */}
         <Route path="/dashboard" element={<POReviewPage />} />
      </Routes>
    </Router>
  );
}

export default App;

import React from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, ArrowRight } from "lucide-react";
import "../styles/welcome.css";

const WelcomePage = () => {
  const navigate = useNavigate();
  
  return (
      <section className="cta-section">
        <div className="cta-content">
          <TrendingUp size={48} className="cta-icon" />
          <h2 className="cta-title">Ready to Transform Your Workflow?</h2>
          <p className="cta-description">
            Start matching invoices and purchase orders in minutes
          </p>
          <button className="btn-cta" onClick={() => navigate("/upload")}>
            Start Matching Now
            <ArrowRight size={20} />
          </button>
        </div>
      </section>
  );
};

export default WelcomePage;
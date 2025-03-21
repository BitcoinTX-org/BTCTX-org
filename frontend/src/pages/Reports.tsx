// FILE: src/pages/Reports.tsx

import React, { useState } from "react";
import "../styles/reports.css";

// Adjust this to match your actual backend's URL
const API_BASE = "http://localhost:8000";

const Reports: React.FC = () => {
  // For other existing reports (e.g. "Complete Tax Report"), store a year.
  const [taxYear, setTaxYear] = useState("");

  // For the Transaction History export, store year & file format separately.
  const [historyYear, setHistoryYear] = useState("");
  const [historyFormat, setHistoryFormat] = useState("PDF");

  // Example existing "reports" array for your other reports
  const otherReports = [
    {
      title: "Complete Tax Report",
      description: "Generate a full tax summary.",
      endpoint: "/reports/comprehensive_tax", // your actual backend route
      needsYearInput: true,
      fileExtension: "pdf",
    },
    {
      title: "Form 8949 (Placeholder)",
      description: "Generate Form 8949 PDF",
      endpoint: "/reports/form_8949", // your actual backend route
      needsYearInput: true,
      fileExtension: "pdf",
    },
  ];

  // Handler for older endpoints (Complete Tax, Form8949, etc.)
  const handleGenerateOtherReport = async (report: typeof otherReports[0]) => {
    if (report.needsYearInput && !taxYear) {
      alert("Please enter a tax year (e.g. 2024).");
      return;
    }

    try {
      const url = `${API_BASE}${report.endpoint}?year=${taxYear}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const blob = await response.blob();
      const extension = report.fileExtension || "pdf";
      const safeTitle = report.title.replace(/\s+/g, "");
      const fileName = `${safeTitle}_${taxYear || "latest"}.${extension}`;

      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error(`Error generating "${report.title}":`, err);
      alert(`Failed to generate ${report.title}. See console for details.`);
    }
  };

  // Handler for the new Transaction History export
  const handleExportTransactionHistory = async () => {
    if (!historyYear) {
      alert("Please enter a year (e.g., 2025) for Transaction History.");
      return;
    }

    try {
      // e.g.: /reports/transaction_history_export?year=2025&fmt=PDF
      const url = `${API_BASE}/reports/transaction_history_export?year=${historyYear}&fmt=${historyFormat}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const blob = await response.blob();
      const safeTitle = `TransactionHistory`;
      const fileName = `${safeTitle}_${historyYear}.${historyFormat.toLowerCase()}`;

      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("Error exporting transaction history:", err);
      alert("Failed to export Transaction History. See console for details.");
    }
  };

  return (
    <div className="reports-container">
      <h2 className="reports-title">Reports</h2>
      <p className="reports-description">
        Generate or view financial and tax reports.
      </p>

      {/* Section for existing reports (Complete Tax, etc.) */}
      <div className="reports-section">
        {otherReports.map((report, index) => (
          <div key={index} className="report-option">
            <div>
              <span className="report-title">{report.title}</span>
              <p className="report-subtitle">{report.description}</p>
            </div>

            {report.needsYearInput && (
              <input
                type="text"
                className="report-year-input"
                placeholder="Enter Year (e.g. 2024)"
                value={taxYear}
                onChange={(e) => setTaxYear(e.target.value)}
              />
            )}

            <button className="report-button" onClick={() => handleGenerateOtherReport(report)}>
              Generate
            </button>
          </div>
        ))}
      </div>

      {/* New section for Transaction History Export */}
      <div className="reports-section">
        <div className="report-option">
          <div>
            <span className="report-title">Transaction History Export</span>
            <p className="report-subtitle">
              Export all Deposits, Withdrawals, Transfers, Buys, Sells for a selected year.
              If the chosen year is the current year, it will automatically export 
              up to today's date.
            </p>
          </div>

          {/* Input for year */}
          <input
            type="text"
            className="report-year-input"
            placeholder="Enter Year (e.g. 2025)"
            value={historyYear}
            onChange={(e) => setHistoryYear(e.target.value)}
          />

          {/* Dropdown to select PDF or CSV */}
          <label style={{ marginTop: "0.5rem" }}>
            Format:{" "}
            <select
              value={historyFormat}
              onChange={(e) => setHistoryFormat(e.target.value)}
            >
              <option value="PDF">PDF</option>
              <option value="CSV">CSV</option>
            </select>
          </label>

          <button className="report-button" onClick={handleExportTransactionHistory}>
            Export
          </button>
        </div>
      </div>
    </div>
  );
};

export default Reports;

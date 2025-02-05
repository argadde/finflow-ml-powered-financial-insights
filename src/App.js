import { useState } from "react";
import { Bar, Pie } from "react-chartjs-2";
import "chart.js/auto";
import "./App.css";
import logo from "./image.png";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [monthlyDeposits, setMonthlyDeposits] = useState({});
  const [monthlyWithdrawals, setMonthlyWithdrawals] = useState({});
  const [monthlyNetCashFlow, setMonthlyNetCashFlow] = useState({});
  const [recurringExpenses, setRecurringExpenses] = useState({});
  const [selectedMonth, setSelectedMonth] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file && file.type === "application/pdf") {
      setSelectedFile(file);
      setLoading(true);
      const formData = new FormData();
      formData.append("file", file);
      try {
        const response = await fetch("http://127.0.0.1:5000/upload", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          throw new Error("File upload failed.");
        }
        const data = await response.json();
        setTransactions(data.transactions || []);
        setMonthlyDeposits(data.monthly_deposits || {});
        setMonthlyWithdrawals(data.monthly_withdrawals || {});
        setMonthlyNetCashFlow(data.monthly_net_cash_flow || {});
        setRecurringExpenses(data.recurring_expenses || {});
      } catch (error) {
        setError("Error processing file.");
        console.error("Error:", error);
      }
      setLoading(false);
    } else {
      alert("Please select a valid PDF file.");
    }
  };

  // Get available months from monthlyDeposits
  const months = Object.keys(monthlyDeposits);

  // Prepare data for the bar chart
  const chartLabels = selectedMonth ? [selectedMonth] : months;
  const barChartData = {
    labels: chartLabels,
    datasets: [
      {
        label: "Deposits",
        data: chartLabels.map((month) => monthlyDeposits[month] || 0),
        backgroundColor: "rgba(75,192,192,0.6)",
      },
      {
        label: "Withdrawals",
        data: chartLabels.map((month) => monthlyWithdrawals[month] || 0),
        backgroundColor: "rgba(255,99,132,0.6)",
      },
    ],
  };

  // Convert transaction date string ("04 Sep 2019") to "YYYY-MM"
  const getYearMonth = (dateStr) => {
    const dateObj = new Date(dateStr);
    if (isNaN(dateObj)) return "";
    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
  };

  // Filter transactions based on the selected month
  const filteredTransactions = selectedMonth
    ? transactions.filter((t) => getYearMonth(t.Date) === selectedMonth)
    : transactions;

  // Calculate frequency for Predicted Category for pie chart
  const predictedCategoryCounts = transactions.reduce((acc, t) => {
    const category = t["Predicted Category"];
    if (category) {
      acc[category] = (acc[category] || 0) + 1;
    }
    return acc;
  }, {});

  // Set up pie chart
  const pieLabels = Object.keys(predictedCategoryCounts);
  const pieDataValues = pieLabels.map((label) => predictedCategoryCounts[label]);
  const pieChartData = {
    labels: pieLabels,
    datasets: [
      {
        data: pieDataValues,
        backgroundColor: [
          "rgba(255, 99, 132, 0.6)",
          "rgba(54, 162, 235, 0.6)",
          "rgba(255, 206, 86, 0.6)",
          "rgba(75, 192, 192, 0.6)",
          "rgba(153, 102, 255, 0.6)",
          "rgba(255, 159, 64, 0.6)",
        ],
      },
    ],
  };

  return (
    <div className="container">
      {/* Logo */}
      <img src={logo} alt="Bank Logo" className="logo" />

      {/* Upload Box */}
      <div className="upload-box">
        <p className="instructions">Upload bank statement here:</p>
        <label htmlFor="fileUpload" className="upload-label">
          <input
            id="fileUpload"
            type="file"
            accept="application/pdf"
            className="file-input"
            onChange={handleFileChange}
          />
          <span className="upload-text">
            {selectedFile ? selectedFile.name : "Choose a PDF file"}
          </span>
        </label>
        {selectedFile && (
          <div className="file-preview">
            <p>📄 {selectedFile.name}</p>
          </div>
        )}
      </div>

      {/* Only show dashboard when not loading */}
      {!loading && months.length > 0 && (
        <>
          {/* Chart Container */}
          <div className="chart-container">
            <h3>Monthly Financial Insights</h3>
            <div>
              <label htmlFor="monthSelect">Select Month: </label>
              <select
                id="monthSelect"
                onChange={(e) => setSelectedMonth(e.target.value)}
                value={selectedMonth}
              >
                <option value="">All Months</option>
                {months.map((month, idx) => (
                  <option key={idx} value={month}>
                    {month}
                  </option>
                ))}
              </select>
              <Bar data={barChartData} />
            </div>
          </div>

          {/* Financial Insights Container */}
          <div className="insights-container">
            <h3>Financial Insights</h3>
            <div className="insight-section">
              <h4>Monthly Deposits</h4>
              <ul>
                {Object.entries(monthlyDeposits).map(([month, amount]) => (
                  <li key={month}>
                    {month}: ${Number(amount).toFixed(2)}
                  </li>
                ))}
              </ul>
            </div>
            <div className="insight-section">
              <h4>Monthly Withdrawals</h4>
              <ul>
                {Object.entries(monthlyWithdrawals).map(([month, amount]) => (
                  <li key={month}>
                    {month}: ${Number(amount).toFixed(2)}
                  </li>
                ))}
              </ul>
            </div>
            <div className="insight-section">
              <h4>Monthly Net Cash Flow</h4>
              <ul>
                {Object.entries(monthlyNetCashFlow).map(([month, net]) => (
                  <li key={month}>
                    {month}: ${Number(net).toFixed(2)}
                  </li>
                ))}
              </ul>
            </div>
            <div className="insight-section">
              <h4>Recurring Expenses</h4>
              <ul>
                {Object.entries(recurringExpenses).map(([vendor, count]) => (
                  <li key={vendor}>
                    {vendor}: {count}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Predicted Category Pie Chart */}
          <div className="pie-container">
            <h3>Categorical Distribution</h3>
            {pieLabels.length > 0 ? (
              <Pie data={pieChartData} />
            ) : (
              <p>No category data available.</p>
            )}
          </div>

          {/* Transactions Container */}
          <div className="transactions-container">
            <h3>Transactions {selectedMonth && `for ${selectedMonth}`}</h3>
            <ul>
              {filteredTransactions.map((t, index) => (
                <li key={index}>
                  {t.Date} - {t.Description} - $
                  {Number(t.Amount).toFixed(2)} - {t["Transaction Type"]} - Predicted:{" "}
                  {t["Predicted Category"]}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {loading && <p>Processing file... Please wait.</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}

export default App;

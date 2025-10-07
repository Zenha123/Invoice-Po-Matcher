// import React, { useState, useEffect } from "react";
// import { useLocation, useNavigate } from "react-router-dom";
// import axios from "axios";
// import {
//   FileText,
//   AlertTriangle,
//   Download,
//   ClipboardList,
//   DollarSign,
//   CheckCircle,
//   XCircle,
//   ChevronRight,
//   Zap,
//   Shield,
//   Clock,
//   Eye,
//   ChevronDown,
//   ChevronUp,
//   AlertCircle,
//   X,
//   ArrowLeft,
// } from "lucide-react";
// import "../styles/dashboard.css";

// // API base URL
// const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// const POReviewPage = () => {
//   const [view, setView] = useState("All");
//   const [selectedDocument, setSelectedDocument] = useState(null);
//   const [selectedInvoice, setSelectedInvoice] = useState(null);
//   const [matchData, setMatchData] = useState([]);
//   const [documents, setDocuments] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
  
//   const location = useLocation();
//   const navigate = useNavigate();
  
//   // Get PO ID from URL query params
//   const searchParams = new URLSearchParams(location.search);
//   const poId = searchParams.get('po_id');

//   // Fetch review page data on mount
//   useEffect(() => {
//     fetchReviewPageData();
//   }, [poId]);

//   const fetchReviewPageData = async () => {
//     try {
//       setLoading(true);
//       setError(null);
      
//       // Build URL with optional po_id filter
//       let url = `${API_BASE_URL}/api/dashboard/review-page-data/`;
//       if (poId) {
//         url += `?po_id=${poId}`;
//       }
      
//       const response = await axios.get(url);
      
//       setMatchData(response.data.match_data || []);
//       setDocuments(response.data.documents || []);
//     } catch (err) {
//       console.error('Error fetching review page data:', err);
//       setError('Failed to load review data. Please refresh the page.');
//     } finally {
//       setLoading(false);
//     }
//   };

//   const StatusBadge = ({ status, description }) => (
//     <div className={`status-badge ${status.toLowerCase().replace(' ', '-')}`}>
//       <div className="status-badge-content">
//         <span className="status-text">{status}</span>
//         <span className="status-desc">{description}</span>
//       </div>
//     </div>
//   );

//   const handleDocumentClick = (doc) => {
//     if (selectedDocument?.id === doc.id) {
//       setSelectedDocument(null);
//       setSelectedInvoice(null);
//     } else {
//       setSelectedDocument(doc);
//       setSelectedInvoice(null);
//     }
//   };

//   const handleInvoiceView = (invoice) => {
//     if (selectedInvoice?.id === invoice.id) {
//       setSelectedInvoice(null);
//     } else {
//       setSelectedInvoice(invoice);
//     }
//   };

//   // Render icon based on string name from API
//   const renderIcon = (iconName, size = 24) => {
//     const icons = {
//       CheckCircle: <CheckCircle size={size} />,
//       XCircle: <XCircle size={size} />,
//       ClipboardList: <ClipboardList size={size} />,
//       DollarSign: <DollarSign size={size} />,
//     };
//     return icons[iconName] || <FileText size={size} />;
//   };

//   const renderPOItems = (po) => (
//     <div className="document-details">
//       <div className="document-header">
//         <h4>Purchase Order Details - {po.po_number || po.poNumber}</h4>
//         <div className="document-meta">
//           <span>Vendor: {po.vendor}</span>
//           <span>Date: {po.date}</span>
//           <span>Total: ${parseFloat(po.total_amount || po.totalAmount).toLocaleString()}</span>
//         </div>
//       </div>
      
//       <div className="items-table-container">
//         <table className="items-table">
//           <thead>
//             <tr>
//               <th>Item Name</th>
//               <th>Quantity</th>
//               <th>Unit Price</th>
//               <th>Subtotal</th>
//             </tr>
//           </thead>
//           <tbody>
//             {(po.items_list || po.itemsList || []).map((item, idx) => (
//               <tr key={item.id || idx}>
//                 <td className="item-name">{item.description}</td>
//                 <td className="item-quantity item-center">{item.quantity}</td>
//                 <td className="item-price item-center">${parseFloat(item.unit_price || item.unitPrice).toLocaleString()}</td>
//                 <td className="item-subtotal item-center">${(item.quantity * parseFloat(item.unit_price || item.unitPrice)).toLocaleString()}</td>
//               </tr>
//             ))}
//           </tbody>
//           <tfoot>
//             <tr>
//               <td colSpan="3" className="total-label item-center">Grand Total</td>
//               <td className="grand-total item-center">${parseFloat(po.total_amount || po.totalAmount).toLocaleString()}</td>
//             </tr>
//           </tfoot>
//         </table>
//       </div>
//     </div>
//   );

//   const renderInvoiceList = (invoicesDoc) => (
//     <div className="document-details">
//       <div className="document-header">
//         <h4>{invoicesDoc.desc || 'Invoice List'}</h4>
//         <p>Total of {invoicesDoc.invoices.length} invoices</p>
//       </div>
      
//       <div className="invoices-table-container">
//         <table className="invoices-table">
//           <thead>
//             <tr>
//               <th>Invoice Number</th>
//               <th>Date</th>
//               <th>Amount</th>
//               <th>Action</th>
//             </tr>
//           </thead>
//           <tbody>
//             {invoicesDoc.invoices.map((invoice, idx) => (
//               <React.Fragment key={invoice.id || idx}>
//                 <tr className="invoice-row">
//                   <td className="invoice-number item-center">{invoice.invoice_number || invoice.invoiceNumber}</td>
//                   <td className="invoice-date item-center">{invoice.date}</td>
//                   <td className="invoice-amount item-center">${parseFloat(invoice.amount).toLocaleString()}</td>
//                   <td className="item-center">
//                     <button 
//                       className="view-invoice-btn"
//                       onClick={() => handleInvoiceView(invoice)}
//                     >
//                       <Eye size={16} />
//                       {selectedInvoice?.id === invoice.id ? 'Hide' : 'View'} Items
//                       {selectedInvoice?.id === invoice.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
//                     </button>
//                   </td>
//                 </tr>
//                 {selectedInvoice?.id === invoice.id && (
//                   <tr className="invoice-details-row">
//                     <td colSpan="4">
//                       <div className="invoice-items-details">
//                         <h5>Items in {invoice.invoice_number || invoice.invoiceNumber}</h5>
//                         <table className="items-table">
//                           <thead>
//                             <tr>
//                               <th>Item Name</th>
//                               <th>Quantity</th>
//                               <th>Unit Price</th>
//                               <th>Subtotal</th>
//                             </tr>
//                           </thead>
//                           <tbody>
//                             {(invoice.items || []).map((item, itemIdx) => (
//                               <tr key={item.id || itemIdx}>
//                                 <td className="item-name">{item.description}</td>
//                                 <td className="item-quantity item-center">{item.quantity}</td>
//                                 <td className="item-price item-center">${parseFloat(item.unit_price || item.unitPrice).toLocaleString()}</td>
//                                 <td className="item-subtotal item-center">${(item.quantity * parseFloat(item.unit_price || item.unitPrice)).toLocaleString()}</td>
//                               </tr>
//                             ))}
//                           </tbody>
//                           <tfoot>
//                             <tr>
//                               <td colSpan="3" className="total-label item-center">Invoice Total</td>
//                               <td className="grand-total item-center">${parseFloat(invoice.amount).toLocaleString()}</td>
//                             </tr>
//                           </tfoot>
//                         </table>
//                       </div>
//                     </td>
//                   </tr>
//                 )}
//               </React.Fragment>
//             ))}
//           </tbody>
//         </table>
//       </div>
//     </div>
//   );

//   if (loading) {
//     return (
//       <div className="dashboard-container">
//         <div className="loading-state">
//           <div className="loading-spinner"></div>
//           <p>Loading review data...</p>
//         </div>
//       </div>
//     );
//   }

//   return (
//     <div className="dashboard-container">
//       {/* Header */}
//       <header className="page-header">
//         <div className="header-nav">
//           {poId && (
//             <button 
//               className="back-button"
//               onClick={() => navigate('/')}
//             >
//               <ArrowLeft size={20} />
//               Back to Upload
//             </button>
//           )}
//         </div>
//         <FileText size={36} className="header-icon" />
//         <div>
//           <h1 className="page-title">Invoice & PO Matching Tool</h1>
//           <p className="page-subtitle">
//             Quickly verify that your purchase orders, goods receipts, and
//             invoices match correctly.
//           </p>
//         </div>
//       </header>

//       {/* Error Message */}
//       {error && (
//         <div className="error-banner">
//           <AlertCircle size={20} />
//           <span>{error}</span>
//           <button onClick={() => setError(null)}>
//             <X size={16} />
//           </button>
//         </div>
//       )}

//       {/* Main Card */}
//       <section className="po-card">
//         {/* Comparison Table */}
//         <div className="table-section">
//           <div className="table-wrapper">
//             {matchData.length > 0 ? (
//               <table className="match-table">
//                 <thead>
//                   <tr>
//                     <th>Status</th>
//                     <th>Details</th>
//                     <th>Insights</th>
//                   </tr>
//                 </thead>
//                 <tbody>
//                   {matchData.map((item, idx) => (
//                     <tr key={item.id || idx} className={`match-row ${item.type}`}>
//                       <td>
//                         <div className="status-column">
//                           <div className="status-icon-wrapper">
//                             {renderIcon(item.icon, 24)}
//                           </div>
//                           <div className="status-info">
//                             <h4 className="status-title">{item.title}</h4>
//                             <p className="status-description">{item.description}</p>
//                             <div className="timestamp">
//                               <Clock size={12} />
//                               {item.timestamp}
//                             </div>
//                           </div>
//                         </div>
//                       </td>
//                       <td>
//                         <div className="details-column">
//                           <div className="details-list">
//                             {item.details.map((detail, detailIdx) => (
//                               <div key={detailIdx} className={`detail-item ${detail.match ? 'match' : 'mismatch'}`}>
//                                 <div className="detail-indicator"></div>
//                                 <span>{detail.text}</span>
//                               </div>
//                             ))}
//                           </div>
//                         </div>
//                       </td>
//                       <td>
//                         <StatusBadge 
//                           status={item.final_status || item.finalStatus} 
//                           description={item.status_description || item.statusDescription} 
//                         />
//                       </td>
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             ) : (
//               <div className="empty-state">
//                 <FileText size={48} className="empty-icon" />
//                 <p>No verification results available</p>
//                 <p className="empty-subtitle">Upload and match documents to see results here</p>
//               </div>
//             )}
//           </div>
//         </div>

//         {/* Document Section */}
//         {documents.length > 0 && (
//           <div className="docs-section">
//             <h3>
//               <FileText className="icon-muted" size={18} /> Document Details
//             </h3>
//             <p>Click on any document to view its details:</p>

//             <div className="doc-list">
//               {documents.map((doc) => (
//                 <div key={doc.id} className="doc-section">
//                   <div 
//                     className={`doc-card ${selectedDocument?.id === doc.id ? 'active' : ''}`}
//                     onClick={() => handleDocumentClick(doc)}
//                   >
//                     <div className="doc-info">
//                       <div className="doc-icon">{renderIcon(doc.icon, 22)}</div>
//                       <div>
//                         <h4>{doc.title}</h4>
//                         <p>{doc.desc}</p>
//                       </div>
//                     </div>
//                     <div className="doc-actions">
//                       <span className="doc-count">{doc.items} items</span>
//                       {selectedDocument?.id === doc.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
//                     </div>
//                   </div>
                  
//                   {selectedDocument?.id === doc.id && (
//                     doc.type === 'po' 
//                       ? renderPOItems(doc)
//                       : renderInvoiceList(doc)
//                   )}
//                 </div>
//               ))}
//             </div>
//           </div>
//         )}
//       </section>
//     </div>
//   );
// };

// export default POReviewPage;




import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  FileText,
  AlertTriangle,
  Download,
  ClipboardList,
  DollarSign,
  CheckCircle,
  XCircle,
  ChevronRight,
  Zap,
  Shield,
  Clock,
  Eye,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  X,
  ArrowLeft,
} from "lucide-react";
import "../styles/dashboard.css";

// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const POReviewPage = () => {
  const [view, setView] = useState("All");
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [matchData, setMatchData] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get PO ID from URL query params
  const searchParams = new URLSearchParams(location.search);
  const poId = searchParams.get('po_id');

  // Fetch review page data on mount
  useEffect(() => {
    fetchReviewPageData();
  }, [poId]);

  const fetchReviewPageData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Build URL with optional po_id filter
      let url = `${API_BASE_URL}/api/dashboard/review-page-data/`;
      if (poId) {
        url += `?po_id=${poId}`;
      }
      
      const response = await axios.get(url);
      
      setMatchData(response.data.match_data || []);
      setDocuments(response.data.documents || []);
    } catch (err) {
      console.error('Error fetching review page data:', err);
      setError('Failed to load review data. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  const StatusBadge = ({ status, description }) => (
    <div className={`status-badge ${status.toLowerCase().replace(' ', '-')}`}>
      <div className="status-badge-content">
        <span className="status-text">{status}</span>
        <span className="status-desc">{description}</span>
      </div>
    </div>
  );

  const handleDocumentClick = (doc) => {
    if (selectedDocument?.id === doc.id) {
      setSelectedDocument(null);
      setSelectedInvoice(null);
    } else {
      setSelectedDocument(doc);
      setSelectedInvoice(null);
    }
  };

  const handleInvoiceView = (invoice) => {
    if (selectedInvoice?.id === invoice.id) {
      setSelectedInvoice(null);
    } else {
      setSelectedInvoice(invoice);
    }
  };

  // Render icon based on string name from API
  const renderIcon = (iconName, size = 24) => {
    const icons = {
      CheckCircle: <CheckCircle size={size} />,
      XCircle: <XCircle size={size} />,
      ClipboardList: <ClipboardList size={size} />,
      DollarSign: <DollarSign size={size} />,
    };
    return icons[iconName] || <FileText size={size} />;
  };

  const renderPOItems = (po) => (
    <div className="document-details">
      <div className="document-header">
        <h4>Purchase Order Details - {po.po_number || po.poNumber}</h4>
        <div className="document-meta">
          <span>Vendor: {po.vendor}</span>
          <span>Date: {po.date}</span>
          <span>Total: ${parseFloat(po.total_amount || po.totalAmount).toLocaleString()}</span>
        </div>
      </div>
      
      <div className="items-table-container">
        <table className="items-table">
          <thead>
            <tr>
              <th>Item Name</th>
              <th>Quantity</th>
              <th>Unit Price</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {(po.items_list || po.itemsList || []).map((item, idx) => (
              <tr key={item.id || idx}>
                <td className="item-name">{item.description}</td>
                <td className="item-quantity item-center">{item.quantity}</td>
                <td className="item-price item-center">${parseFloat(item.unit_price || item.unitPrice).toLocaleString()}</td>
                <td className="item-subtotal item-center">${(item.quantity * parseFloat(item.unit_price || item.unitPrice)).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan="3" className="total-label item-center">Grand Total</td>
              <td className="grand-total item-center">${parseFloat(po.total_amount || po.totalAmount).toLocaleString()}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );

  const renderInvoiceList = (invoicesDoc) => (
    <div className="document-details">
      <div className="document-header">
        <h4>{invoicesDoc.desc || 'Invoice List'}</h4>
        <p>Total of {invoicesDoc.invoices.length} invoices</p>
      </div>
      
      <div className="invoices-table-container">
        <table className="invoices-table">
          <thead>
            <tr>
              <th>Invoice Number</th>
              <th>Date</th>
              <th>Amount</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {invoicesDoc.invoices.map((invoice, idx) => (
              <React.Fragment key={invoice.id || idx}>
                <tr className="invoice-row">
                  <td className="invoice-number item-center">{invoice.invoice_number || invoice.invoiceNumber}</td>
                  <td className="invoice-date item-center">{invoice.date}</td>
                  <td className="invoice-amount item-center">${parseFloat(invoice.amount).toLocaleString()}</td>
                  <td className="item-center">
                    <button 
                      className="view-invoice-btn"
                      onClick={() => handleInvoiceView(invoice)}
                    >
                      <Eye size={16} />
                      {selectedInvoice?.id === invoice.id ? 'Hide' : 'View'} Items
                      {selectedInvoice?.id === invoice.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </td>
                </tr>
                {selectedInvoice?.id === invoice.id && (
                  <tr className="invoice-details-row">
                    <td colSpan="4">
                      <div className="invoice-items-details">
                        <h5>Items in {invoice.invoice_number || invoice.invoiceNumber}</h5>
                        <table className="items-table">
                          <thead>
                            <tr>
                              <th>Item Name</th>
                              <th>Quantity</th>
                              <th>Unit Price</th>
                              <th>Subtotal</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(invoice.items || []).map((item, itemIdx) => (
                              <tr key={item.id || itemIdx}>
                                <td className="item-name">{item.description}</td>
                                <td className="item-quantity item-center">{item.quantity}</td>
                                <td className="item-price item-center">${parseFloat(item.unit_price || item.unitPrice).toLocaleString()}</td>
                                <td className="item-subtotal item-center">${(item.quantity * parseFloat(item.unit_price || item.unitPrice)).toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot>
                            <tr>
                              <td colSpan="3" className="total-label item-center">Invoice Total</td>
                              <td className="grand-total item-center">${parseFloat(invoice.amount).toLocaleString()}</td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading review data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="page-header">
        <FileText size={36} className="header-icon" />
        <div>
          <h1 className="page-title">Invoice & PO Matching Tool</h1>
          <p className="page-subtitle">
            Quickly verify that your purchase orders, goods receipts, and
            invoices match correctly.
          </p>
        </div>
      </header>

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Main Card */}
      <section className="po-card">
        {/* Comparison Table */}
        <div className="table-section">
          <div className="table-wrapper">
            {matchData.length > 0 ? (
              <table className="match-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Details</th>
                    <th>Insights</th>
                  </tr>
                </thead>
                <tbody>
                  {matchData.map((item, idx) => (
                    <tr key={item.id || idx} className={`match-row ${item.type}`}>
                      <td>
                        <div className="status-column">
                          <div className="status-icon-wrapper">
                            {renderIcon(item.icon, 24)}
                          </div>
                          <div className="status-info">
                            <h4 className="status-title">{item.title}</h4>
                            <p className="status-description">{item.description}</p>
                            <div className="timestamp">
                              <Clock size={12} />
                              {item.timestamp}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="details-column">
                          <div className="details-list">
                            {item.details.map((detail, detailIdx) => (
                              <div key={detailIdx} className={`detail-item ${detail.match ? 'match' : 'mismatch'}`}>
                                <div className="detail-indicator"></div>
                                <span>{detail.text}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </td>
                      <td>
                        <StatusBadge 
                          status={item.final_status || item.finalStatus} 
                          description={item.status_description || item.statusDescription} 
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">
                <FileText size={48} className="empty-icon" />
                <p>No verification results available</p>
                <p className="empty-subtitle">Upload and match documents to see results here</p>
              </div>
            )}
          </div>
        </div>

        {/* Document Section */}
        {documents.length > 0 && (
          <div className="docs-section">
            <h3>
              <FileText className="icon-muted" size={18} /> Document Details
            </h3>
            <p>Click on any document to view its details:</p>

            <div className="doc-list">
              {documents.map((doc) => (
                <div key={doc.id} className="doc-section">
                  <div 
                    className={`doc-card ${selectedDocument?.id === doc.id ? 'active' : ''}`}
                    onClick={() => handleDocumentClick(doc)}
                  >
                    <div className="doc-info">
                      <div className="doc-icon">{renderIcon(doc.icon, 22)}</div>
                      <div>
                        <h4>{doc.title}</h4>
                        <p>{doc.desc}</p>
                      </div>
                    </div>
                    <div className="doc-actions">
                      <span className="doc-count">{doc.items} items</span>
                      {selectedDocument?.id === doc.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>
                  </div>
                  
                  {selectedDocument?.id === doc.id && (
                    doc.type === 'po' 
                      ? renderPOItems(doc)
                      : renderInvoiceList(doc)
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Back to Upload Button - Positioned at bottom left */}
        {poId && (
          <div className="bottom-nav">
            <button 
              className="back-button"
              onClick={() => navigate('/upload')}
            >
              <ArrowLeft size={20} />
              Back to Upload
            </button>
          </div>
        )}
      </section>
    </div>
  );
};

export default POReviewPage;
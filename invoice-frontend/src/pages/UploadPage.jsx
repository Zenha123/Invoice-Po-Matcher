import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { FileText, Upload, X, Plus, CloudUpload, CheckCircle, AlertCircle } from "lucide-react";
import "../styles/dashboard.css";

// API base URL - adjust as needed
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Upload Modal Component
const UploadModal = ({ isOpen, onClose, title, onUpload, acceptedTypes = ".pdf,.png,.jpg,.jpeg", isLoading = false }) => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    setSelectedFiles(files);
  };

  const handleSubmit = () => {
    if (selectedFiles.length > 0) {
      onUpload(selectedFiles);
      setSelectedFiles([]);
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  useEffect(() => {
    if (!isOpen) {
      setSelectedFiles([]);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close-btn" onClick={onClose} disabled={isLoading}>
            <X size={20} />
          </button>
        </div>
        
        <div className="modal-body">
          <div 
            className={`upload-area ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <CloudUpload size={48} className="upload-icon" />
            <p>Drag and drop files here or click to browse</p>
            <p className="upload-hint">Supports: PDF, PNG, JPG (Max 10MB each)</p>
            <input
              type="file"
              multiple
              onChange={handleFileSelect}
              accept={acceptedTypes}
              className="file-input"
              disabled={isLoading}
            />
          </div>
          
          {selectedFiles.length > 0 && (
            <div className="selected-files">
              <h4>Selected Files ({selectedFiles.length}):</h4>
              <div className="files-list">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="file-item">
                    <FileText size={16} />
                    <div className="file-info">
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                    </div>
                    <button 
                      className="btn-remove-small"
                      onClick={() => removeFile(index)}
                      disabled={isLoading}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </button>
          <button 
            className="btn-primary" 
            onClick={handleSubmit}
            disabled={selectedFiles.length === 0 || isLoading}
          >
            {isLoading ? (
              <>
                <div className="loading-spinner"></div>
                Uploading...
              </>
            ) : (
              <>
                <Upload size={16} />
                Upload {selectedFiles.length > 0 ? `(${selectedFiles.length})` : ''}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

// PO Table Row Component
const POTableRow = ({ po, index, onInvoiceUpload, onRemove, invoices, isUploading, onPOClick }) => {
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  
  // Extract PO number from name
  const poNumber = po.name ? po.name.replace('.pdf', '') : po.purchase_order_id;
  
  // Check if this PO has any invoices
  const poInvoices = invoices.filter(inv => inv.linked_po === po.name);
  const invoiceCount = po.invoice_count || poInvoices.length;

  // Determine status based on invoices
  const getStatus = () => {
    if (invoiceCount === 0) return { text: "No Invoices", type: "pending" };
    if (invoiceCount === 1) return { text: "Invoice Ready", type: "ready" };
    return { text: `${invoiceCount} Invoices`, type: "completed" };
  };

  const status = getStatus();

  return (
    <>
      <tr className="po-table-row">
        <td className="po-number-cell">
          <div 
            className="po-number clickable" 
            onClick={() => onPOClick(po.id)}
            style={{ cursor: 'pointer' }}
          >
            <FileText size={16} className="icon-muted" />
            <span className="po-number-text">{poNumber}</span>
          </div>
        </td>
        <td className="status-cell">
          <div className={`status-badge ${status.type}`}>
            {status.text}
            {status.type === "completed" && <CheckCircle size={12} />}
          </div>
        </td>
        <td className="invoice-count-cell">
          <span className="invoice-count">{invoiceCount}</span>
        </td>
        <td className="upload-date-cell">
          {po.upload_date || po.uploadDate}
        </td>
        <td className="actions-cell">
          <div className="table-actions">
            <button 
              className={`btn-upload-invoice ${invoiceCount > 0 ? 'has-invoices' : ''}`}
              onClick={() => setShowInvoiceModal(true)}
              disabled={isUploading}
            >
              <Plus size={14} />
              {invoiceCount > 0 ? 'Add More' : 'Upload Invoice'}
            </button>
            <button 
              className="btn-remove-table"
              onClick={() => onRemove(index)}
              title="Remove PO"
              disabled={isUploading}
            >
              <X size={14} />
            </button>
          </div>
        </td>
      </tr>

      <UploadModal
        isOpen={showInvoiceModal}
        onClose={() => setShowInvoiceModal(false)}
        title={`Upload Invoice for ${poNumber}`}
        onUpload={(files) => onInvoiceUpload(po.id, files)}
        isLoading={isUploading}
      />
    </>
  );
};

// Main Upload Page Component
const UploadPage = () => {
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showPOModal, setShowPOModal] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Fetch initial data
  useEffect(() => {
    fetchUploadPageData();
  }, []);

  const fetchUploadPageData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/home/upload-page-data/`);
      
      setPurchaseOrders(response.data.purchase_orders || []);
      setInvoices(response.data.invoices || []);
    } catch (err) {
      console.error('Error fetching upload page data:', err);
      setError('Failed to load data. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  // Handle PO upload
  const handlePOUpload = async (files) => {
    try {
      setUploading(true);
      setError(null);

      // Upload each file
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('filename', file.name);

        await axios.post(`${API_BASE_URL}/api/home/po/upload/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }

      // Refresh data after upload
      await fetchUploadPageData();
      setShowPOModal(false);
      
    } catch (err) {
      console.error('Error uploading PO:', err);
      setError(err.response?.data?.error || 'Failed to upload purchase order. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  // Handle invoice upload for specific PO
  const handlePOInvoiceUpload = async (poId, files) => {
    try {
      setUploading(true);
      setError(null);

      // Upload each file
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('purchase_order_id', poId);
        formData.append('filename', file.name);

        await axios.post(`${API_BASE_URL}/api/home/invoice/upload-and-verify/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }

      // Refresh data after upload
      await fetchUploadPageData();
      
    } catch (err) {
      console.error('Error uploading invoice:', err);
      setError(err.response?.data?.error || 'Failed to upload invoice. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  // Remove PO (frontend only - you may want to add a DELETE endpoint)
  const removePO = (index) => {
    const poToRemove = purchaseOrders[index];
    setPurchaseOrders(prev => prev.filter((_, i) => i !== index));
    
    // Also remove any invoices linked to this PO
    setInvoices(prev => prev.filter(inv => inv.linked_po !== poToRemove.name));
  };

  // Handle PO click - Navigate to dashboard with PO ID
  const handlePOClick = (poId) => {
    navigate(`/dashboard?po_id=${poId}`);
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading data...</p>
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
          <h1 className="page-title">Document Upload Center</h1>
          <p className="page-subtitle">
            Upload your purchase orders and invoices for automated matching and verification
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
        {/* Action Buttons */}
        <div className="upload-actions">
          <button 
            className="btn-primary large"
            onClick={() => setShowPOModal(true)}
            disabled={uploading}
          >
            <Upload size={20} />
            Upload Purchase Order
          </button>
        </div>

        {/* Purchase Orders Table */}
        <div className="po-table-section">
          <div className="table-header-section">
            <h3>
              <FileText className="icon-muted" size={18} />
              Purchase Orders ({purchaseOrders.length}/6)
            </h3>
            <div className="table-summary">
              {invoices.length > 0 && (
                <span className="invoices-total">
                  {invoices.length} invoice(s) uploaded across {purchaseOrders.filter(po => 
                    invoices.some(inv => inv.linked_po === po.name)
                  ).length} PO(s)
                </span>
              )}
            </div>
          </div>
          
          {purchaseOrders.length > 0 ? (
            <div className="table-container">
              <table className="po-table">
                <thead>
                  <tr>
                    <th className="po-number-header">PO Number</th>
                    <th className="status-header">Status</th>
                    <th className="invoice-count-header">Invoices</th>
                    <th className="upload-date-header">Upload Date</th>
                    <th className="actions-header">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {purchaseOrders.map((po, index) => (
                    <POTableRow
                      key={po.id || index}
                      po={po}
                      index={index}
                      onInvoiceUpload={handlePOInvoiceUpload}
                      onRemove={removePO}
                      invoices={invoices}
                      isUploading={uploading}
                      onPOClick={handlePOClick}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <FileText size={48} className="empty-icon" />
              <p>No purchase orders uploaded yet</p>
              <p className="empty-subtitle">Click the button above to upload your first PO</p>
            </div>
          )}
        </div>
      </section>

      {/* PO Upload Modal */}
      <UploadModal
        isOpen={showPOModal}
        onClose={() => !uploading && setShowPOModal(false)}
        title="Upload Purchase Orders"
        onUpload={handlePOUpload}
        isLoading={uploading}
      />
    </div>
  );
};

export default UploadPage;
//frontend/src/components/TransactionPanel.tsx
import React, { useEffect, useState } from "react";
import "../styles/transactionPanel.css";
import TransactionForm from "./TransactionForm";

interface TransactionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitSuccess?: () => void;
  transactionId?: number | null; // For editing
}

const TransactionPanel: React.FC<TransactionPanelProps> = ({
  isOpen,
  onClose,
  onSubmitSuccess,
  transactionId,
}) => {
  const [showDiscardModal, setShowDiscardModal] = useState(false);
  const [isFormDirty, setIsFormDirty] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false); // Tracks form submission status

  useEffect(() => {
    if (isOpen) {
      setShowDiscardModal(false);
      setIsFormDirty(false);
      setIsUpdating(false); 
    }
  }, [isOpen]);

  const handleOverlayClick = () => {
    if (isFormDirty) {
      setShowDiscardModal(true);
    } else {
      onClose();
    }
  };

  const handleDiscardChanges = () => {
    setShowDiscardModal(false);
    onClose();
  };

  const handleGoBack = () => {
    setShowDiscardModal(false);
  };

  const handleFormSubmitSuccess = () => {
    setIsUpdating(false);
    onClose();
    onSubmitSuccess?.();
  };

  const handleUpdateStatusChange = (updating: boolean) => {
    setIsUpdating(updating);
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="transaction-panel-overlay" onClick={handleOverlayClick} />
      <div className="transaction-panel">
        <div className="panel-header">
          <h2>{transactionId ? "Edit Transaction" : "Add Transaction"}</h2>
        </div>

        <div className="panel-body">
          <TransactionForm
            id="transaction-form"
            onDirtyChange={setIsFormDirty}
            onSubmitSuccess={handleFormSubmitSuccess}
            transactionId={transactionId}
            onUpdateStatusChange={handleUpdateStatusChange}
          />
        </div>

        <div className="panel-footer" style={{ display: "flex", justifyContent: "flex-end", gap: "1rem" }}>
          {/* Save button on the left */}
          <button
            className="save-button"
            type="submit"
            form="transaction-form"
            disabled={isUpdating}
          >
            {isUpdating
              ? "Saving..."
              : transactionId
              ? "Update Transaction"
              : "Save Transaction"}
          </button>
        
          {/* Delete button only if editing */}
          {transactionId && (
            <button
              type="button"
              className="delete-button danger"
              onClick={() => {
                const confirmed = window.confirm("Are you sure you want to delete this transaction?");
                if (confirmed) {
                  // We’ll call the form’s delete handler
                  const deleteBtn = document.querySelector<HTMLButtonElement>("#trigger-form-delete");
                  deleteBtn?.click();
                }
              }}
              disabled={isUpdating}
            >
              Delete
            </button>
          )}
        </div>

      {showDiscardModal && (
        <div className="discard-modal">
          <div className="discard-modal-content">
            <h3>Discard changes?</h3>
            <p>Your changes have not been saved. If you close this panel, they will be lost.</p>
            <div className="discard-modal-actions">
              <button onClick={handleGoBack}>Go Back</button>
              <button onClick={handleDiscardChanges} className="danger">
                Discard Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default TransactionPanel;

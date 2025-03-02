/**
 * TransactionForm.tsx
 *
 * Pulls all domain-specific types (TransactionType, TransactionFormData, etc.)
 * from your global.d.ts. The only local interface below is TransactionFormProps,
 * which is purely a React prop type you can optionally move to global if desired.
 */

import React, { useState, useEffect } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import axios from "axios";            // For isAxiosError checks
import api from "../api";             // Centralized API client
import "../styles/transactionForm.css";
import { parseDecimal, formatUsd } from "../utils/format"; // Import parsing/formatting utils

/**
 * localDatetimeToIso:
 * Converts a "datetime-local" string (e.g. "2023-09-25T12:34")
 * to a full ISO8601 format for the backend.
 */
function localDatetimeToIso(localDatetime: string): string {
  return new Date(localDatetime).toISOString();
}

/**
 * TransactionFormProps:
 * Local props interface for this component. You could move it
 * to global.d.ts if multiple components rely on these props.
 */
interface TransactionFormProps {
  id?: string;
  onDirtyChange?: (dirty: boolean) => void;
  onSubmitSuccess?: () => void;
}

// ------------------------------------------------------------
// Hardcoded numeric account ID mappings
// ------------------------------------------------------------
const EXTERNAL_ID = 99;       // "External" placeholder account
const EXCHANGE_USD_ID = 3;    // Exchange (USD sub-account)
const EXCHANGE_BTC_ID = 4;    // Exchange (BTC sub-account)

/**
 * mapAccountToId:
 * Convert the user's chosen AccountType + Currency into
 * a numeric ID recognized by the backend.
 *
 * E.g.:
 *   - Bank => 1
 *   - Wallet => 2
 *   - Exchange + BTC => 4
 *   - Exchange + USD => 3
 */
function mapAccountToId(
  account?: AccountType,
  currency?: Currency
): number {
  if (account === "Bank") return 1;
  if (account === "Wallet") return 2;
  if (account === "Exchange") {
    return currency === "BTC" ? EXCHANGE_BTC_ID : EXCHANGE_USD_ID;
  }
  return 0;
}

/**
 * mapDoubleEntryAccounts:
 * Translates single-entry TransactionFormData into from/to IDs
 * for the new double-entry backend payload.
 *
 * We now explicitly return an IAccountMapping, which consists of
 * { from_account_id, to_account_id }.
 */
function mapDoubleEntryAccounts(data: TransactionFormData): IAccountMapping {
  switch (data.type) {
    case "Deposit":
      return {
        from_account_id: EXTERNAL_ID,
        to_account_id: mapAccountToId(data.account, data.currency),
      };
    case "Withdrawal":
      return {
        from_account_id: mapAccountToId(data.account, data.currency),
        to_account_id: EXTERNAL_ID,
      };
    case "Transfer":
      return {
        from_account_id: mapAccountToId(data.fromAccount, data.fromCurrency),
        to_account_id: mapAccountToId(data.toAccount, data.toCurrency),
      };
    case "Buy":
      return {
        from_account_id: EXCHANGE_USD_ID,
        to_account_id: EXCHANGE_BTC_ID,
      };
    case "Sell":
      return {
        from_account_id: EXCHANGE_BTC_ID,
        to_account_id: EXCHANGE_USD_ID,
      };
    default:
      // Should never happen if TransactionType is properly set
      return { from_account_id: 0, to_account_id: 0 };
  }
}

/**
 * TransactionForm:
 * Handles creating/editing a transaction in "single-entry" style.
 * The new backend interprets it as multiple ledger lines behind
 * the scenes (double-entry).
 */
const TransactionForm: React.FC<TransactionFormProps> = ({
  id,
  onDirtyChange,
  onSubmitSuccess,
}) => {
  // react-hook-form setup
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isDirty },
  } = useForm<TransactionFormData>({
    defaultValues: {
      timestamp: new Date().toISOString().slice(0, 16), // e.g. "2025-03-01T12:00"
      fee: 0,
      costBasisUSD: 0,
      proceeds_usd: 0,
    },
  });

  // Local state to track the user-selected transaction type,
  // as well as a display-only USD estimate of any BTC fee (for Transfer).
  const [currentType, setCurrentType] = useState<TransactionType | "">("");
  const [feeInUsdDisplay, setFeeInUsdDisplay] = useState<number>(0);

  // Watch certain fields for dynamic UI logic
  const amountFromVal = watch("amountFrom") || 0;
  const amountToVal = watch("amountTo") || 0;
  const fromCurrencyVal = watch("fromCurrency");
  const accountVal = watch("account");
  const currencyVal = watch("currency");
  const amountUsdVal = watch("amountUSD") || 0; // For Buy/Sell
  const amountBtcVal = watch("amountBTC") || 0; // For Buy/Sell
  const fromAccountVal = watch("fromAccount");

  /**
   * For debugging or logging user inputs (optional)
   */
  useEffect(() => {
    // console.log("User typed in amountUSD:", amountUsdVal);
  }, [amountUsdVal]);

  useEffect(() => {
    // console.log("User typed in amountBTC:", amountBtcVal);
  }, [amountBtcVal]);

  /**
   * Notify parent (if any) about "dirty" (unsaved) form state
   */
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  /**
   * If user selects Deposit or Withdrawal:
   *  - If account = Bank => currency = "USD"
   *  - If account = Wallet => currency = "BTC"
   *  - If account = Exchange => user manually picks currency
   */
  useEffect(() => {
    if (currentType === "Deposit" || currentType === "Withdrawal") {
      if (accountVal === "Bank") {
        setValue("currency", "USD");
      } else if (accountVal === "Wallet") {
        setValue("currency", "BTC");
      }
      // if account=Exchange => do nothing, user chooses
    }
  }, [accountVal, currentType, setValue]);

  /**
   * Transfer logic:
   * - If fromAccount=Bank => fromCurrency=USD => to=Exchange => toCurrency=USD
   * - If fromAccount=Wallet => fromCurrency=BTC => to=Exchange => toCurrency=BTC
   * - If fromAccount=Exchange => auto-set the "toAccount" to be Bank or Wallet
   *   based on fromCurrency
   */
  useEffect(() => {
    if (currentType !== "Transfer") return;

    if (fromAccountVal === "Bank") {
      setValue("fromCurrency", "USD");
      setValue("toAccount", "Exchange");
      setValue("toCurrency", "USD");
    } else if (fromAccountVal === "Wallet") {
      setValue("fromCurrency", "BTC");
      setValue("toAccount", "Exchange");
      setValue("toCurrency", "BTC");
    } else if (fromAccountVal === "Exchange") {
      if (fromCurrencyVal === "USD") {
        setValue("toAccount", "Bank");
        setValue("toCurrency", "USD");
      } else if (fromCurrencyVal === "BTC") {
        setValue("toAccount", "Wallet");
        setValue("toCurrency", "BTC");
      }
    }
  }, [currentType, fromAccountVal, fromCurrencyVal, setValue]);

  /**
   * onTransactionTypeChange:
   * When user changes the transaction type select (e.g. from "Deposit" to "Withdrawal"),
   * we reset the form but keep the newly selected transaction type.
   */
  const onTransactionTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedType = e.target.value as TransactionType;
    setCurrentType(selectedType);

    // Reset the form to default values
    reset({
      type: selectedType,
      timestamp: new Date().toISOString().slice(0, 16),
      fee: 0,
      costBasisUSD: 0,
      proceeds_usd: 0,
    });
  };

  /**
   * showCostBasisField (used within the Deposit rendering logic):
   * We only show cost basis if:
   *  - type = Deposit
   *  - currency = BTC
   *  - account = Wallet or Exchange
   */
  const showCostBasisField =
    currentType === "Deposit" &&
    currencyVal === "BTC" &&
    (accountVal === "Wallet" || accountVal === "Exchange");

  /**
   * If Transfer + fromCurrency=BTC, auto-calc the fee as (amountFrom - amountTo).
   * This logic sets the "fee" field for the user behind the scenes.
   * We also display an approximate USD value (feeInUsdDisplay).
   */
  useEffect(() => {
    if (currentType === "Transfer" && fromCurrencyVal === "BTC") {
      const calcFee = amountFromVal - amountToVal;
      if (calcFee < 0) {
        setValue("fee", 0);
      } else {
        const feeBtc = Number(calcFee.toFixed(8)); // up to 8 decimals
        setValue("fee", feeBtc);

        // Example approximate price to show the user
        const mockBtcPrice = 30000; 
        const approxUsd = feeBtc * mockBtcPrice;
        setFeeInUsdDisplay(Number(approxUsd.toFixed(2)));
      }
    }
  }, [currentType, fromCurrencyVal, amountFromVal, amountToVal, setValue]);

  /**
   * onSubmit:
   * Handle final form submission by constructing an ICreateTransactionPayload
   * and POSTing to /transactions. We parse decimals to ensure numeric fields.
   */
  const onSubmit: SubmitHandler<TransactionFormData> = async (data) => {
    try {
      // (1) If it's a BTC Withdrawal and proceeds_usd was not specified, default to 0
      if (
        data.type === "Withdrawal" &&
        data.currency === "BTC" &&
        !data.proceeds_usd
      ) {
        data.proceeds_usd = 0;
      }

      // (2) Resolve from/to account IDs
      const { from_account_id, to_account_id } = mapDoubleEntryAccounts(data);

      // (3) Convert "datetime-local" to full ISO8601 for the backend
      const isoTimestamp = localDatetimeToIso(data.timestamp);

      // (4) Prepare individual fields
      let amount = 0;
      let feeCurrency: Currency | "USD" | "BTC" = "USD";
      let source: string | undefined;
      let purpose: string | undefined;
      let cost_basis_usd = 0;
      let proceeds_usd: number | undefined = undefined;

      switch (data.type) {
        case "Deposit":
          amount = parseDecimal(data.amount);
          // For Deposits, we no longer show any dynamic fee field, even for BTC.
          // The user can incorporate BTC miner fees into costBasisUSD if desired.
          feeCurrency = data.currency === "BTC" ? "BTC" : "USD";
          source = data.source && data.source !== "N/A" ? data.source : "N/A";
          if (showCostBasisField) {
            cost_basis_usd = parseDecimal(data.costBasisUSD);
          }
          break;

        case "Withdrawal":
          amount = parseDecimal(data.amount);
          feeCurrency = data.currency === "BTC" ? "BTC" : "USD";
          purpose = data.purpose && data.purpose !== "N/A" ? data.purpose : "N/A";
          proceeds_usd = parseDecimal(data.proceeds_usd);
          break;

        case "Transfer":
          amount = parseDecimal(data.amountFrom);
          feeCurrency = data.fromCurrency === "BTC" ? "BTC" : "USD";
          break;

        case "Buy":
          amount = parseDecimal(data.amountBTC);
          feeCurrency = "USD";
          cost_basis_usd = parseDecimal(data.amountUSD);
          break;

        case "Sell":
          amount = parseDecimal(data.amountBTC);
          feeCurrency = "USD";
          proceeds_usd = parseDecimal(data.amountUSD);
          break;

        default:
          // Should never happen if type is enforced via TS
          break;
      }

      // (5) Build final payload for backend
      const transactionPayload: ICreateTransactionPayload = {
        from_account_id,
        to_account_id,
        type: data.type,
        amount,
        timestamp: isoTimestamp,
        fee_amount: parseDecimal(data.fee),
        fee_currency: feeCurrency as Currency,
        cost_basis_usd,
        proceeds_usd,
        source,
        purpose,
        is_locked: false,
      };

      // (6) POST to the backend
      const response = await api.post("/transactions", transactionPayload);
      console.log("Transaction created:", response.data);

      // If the server returns a realized_gain_usd, show an alert with that info
      if (response.data) {
        const createdTx = response.data as ITransactionRaw;
        const rg = createdTx.realized_gain_usd
          ? parseDecimal(createdTx.realized_gain_usd)
          : 0;
        if (rg !== 0) {
          const sign = rg >= 0 ? "+" : "";
          alert(
            `Transaction created successfully!\n` +
            `Realized Gain: ${sign}${formatUsd(rg)}`
          );
        } else {
          alert("Transaction created successfully!");
        }
      } else {
        alert("Transaction created successfully!");
      }

      // Reset form & notify parent
      reset();
      setCurrentType("");
      onSubmitSuccess?.();
    } catch (error: unknown) {
      // If it's an Axios error, we can parse further
      if (axios.isAxiosError<ApiErrorResponse>(error)) {
        const detailMsg = error.response?.data?.detail;
        const fallbackMsg = error.message || "Error";
        const finalMsg = detailMsg || fallbackMsg;

        // If your backend returns field-level errors, you can log them here:
        if (error.response?.data?.errors) {
          console.log("Field-specific errors:", error.response.data.errors);
        }

        alert(`Failed to create transaction: ${finalMsg}`);
      } else if (error instanceof Error) {
        // Generic JS Error
        alert(`Failed to create transaction: ${error.message}`);
      } else {
        // Non-Error object or other unexpected type
        alert("An unexpected error occurred while creating the transaction.");
      }
    }
  };

  /**
   * renderDynamicFields:
   * Renders different sets of form fields depending on the user-selected `currentType`.
   */
  const renderDynamicFields = () => {
    switch (currentType) {
      case "Deposit": {
        const account = watch("account");
        const currency = watch("currency");

        // Previously we had a showFee for BTC deposits, but now we've removed it
        // so there's no dynamic fee for ANY deposit. (See new approach)

        // Show Source if deposit is going into BTC (Wallet or Exchange)
        const showSource =
          account === "Wallet" ||
          (account === "Exchange" && currency === "BTC");

        // Show Cost Basis if BTC deposit into Wallet or Exchange
        const showCostBasisField =
          currentType === "Deposit" &&
          currency === "BTC" &&
          (account === "Wallet" || account === "Exchange");

        return (
          <>
            {/* Account */}
            <div className="form-group">
              <label>Account:</label>
              <select
                className="form-control"
                {...register("account", { required: true })}
              >
                <option value="">Select Account</option>
                <option value="Bank">Bank Account</option>
                <option value="Wallet">Bitcoin Wallet</option>
                <option value="Exchange">Exchange</option>
              </select>
              {errors.account && (
                <span className="error-text">Please select an account</span>
              )}
            </div>

            {/* Currency */}
            <div className="form-group">
              <label>Currency:</label>
              {account === "Exchange" ? (
                <select
                  className="form-control"
                  {...register("currency", { required: true })}
                >
                  <option value="">Select Currency</option>
                  <option value="USD">USD</option>
                  <option value="BTC">BTC</option>
                </select>
              ) : (
                <input
                  type="text"
                  className="form-control"
                  {...register("currency")}
                  readOnly
                />
              )}
              {errors.currency && (
                <span className="error-text">Currency is required</span>
              )}
            </div>

            {/* Amount */}
            <div className="form-group">
              <label>Amount:</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("amount", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amount && (
                <span className="error-text">Amount is required</span>
              )}
            </div>

            {/* Source (only if BTC deposit into Wallet or Exchange) */}
            {showSource && (
              <div className="form-group">
                <label>Source:</label>
                <select
                  className="form-control"
                  {...register("source", { required: true })}
                >
                  <option value="N/A">N/A</option>
                  <option value="MyBTC">MyBTC</option>
                  <option value="Gift">Gift</option>
                  <option value="Income">Income</option>
                  <option value="Interest">Interest</option>
                  <option value="Reward">Reward</option>
                </select>
              </div>
            )}

            {/* No fee field here for deposit (BTC or USD). Removed as per new approach. */}

            {/* Cost Basis (USD), only for BTC deposit */}
            {showCostBasisField && (
              <div className="form-group">
                <label>Cost Basis (USD):</label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  {...register("costBasisUSD", { valueAsNumber: true })}
                />
                {/* 
                  New note to user: If they paid any BTC fee externally, 
                  they should add its USD value to cost basis here.
                */}
                <small style={{ color: "#888", display: "block", marginTop: "4px" }}>
                  If you paid a miner fee in BTC, please add that fee's USD value
                  to your Cost Basis.
                </small>
              </div>
            )}
          </>
        );
      }

      case "Withdrawal": {
        const account = watch("account");
        const currency = watch("currency");
        const feeLabel = currency === "BTC" ? "Fee (BTC)" : "Fee (USD)";

        // Only show "Purpose" if withdrawal is BTC from Wallet or Exchange
        const showPurpose =
          account === "Wallet" ||
          (account === "Exchange" && currency === "BTC");

        // For warning message if user chooses "Spent" but proceeds is 0
        const purposeVal = watch("purpose");
        const proceedsUsdVal = watch("proceeds_usd") ?? 0;

        return (
          <>
            {/* Account */}
            <div className="form-group">
              <label>Account:</label>
              <select
                className="form-control"
                {...register("account", { required: true })}
              >
                <option value="">Select Account</option>
                <option value="Bank">Bank Account</option>
                <option value="Wallet">Bitcoin Wallet</option>
                <option value="Exchange">Exchange</option>
              </select>
              {errors.account && (
                <span className="error-text">Please select an account</span>
              )}
            </div>

            {/* Currency */}
            <div className="form-group">
              <label>Currency:</label>
              {account === "Exchange" ? (
                <select
                  className="form-control"
                  {...register("currency", { required: true })}
                >
                  <option value="">Select Currency</option>
                  <option value="USD">USD</option>
                  <option value="BTC">BTC</option>
                </select>
              ) : (
                <input
                  type="text"
                  className="form-control"
                  {...register("currency")}
                  readOnly
                />
              )}
              {errors.currency && (
                <span className="error-text">Currency is required</span>
              )}
            </div>

            {/* Amount */}
            <div className="form-group">
              <label>Amount:</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("amount", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amount && (
                <span className="error-text">Amount is required</span>
              )}
            </div>

            {/* Purpose (only if BTC withdrawal from Wallet or Exchange) */}
            {showPurpose && (
              <div className="form-group">
                <label>Purpose (BTC only):</label>
                <select
                  className="form-control"
                  {...register("purpose", { required: true })}
                >
                  <option value="">Select Purpose</option>
                  <option value="Spent">Spent</option>
                  <option value="Gift">Gift</option>
                  <option value="Donation">Donation</option>
                  <option value="Lost">Lost</option>
                </select>
              </div>
            )}

            {/* Fee */}
            <div className="form-group">
              <label>{feeLabel}:</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("fee", { valueAsNumber: true })}
              />
            </div>

            {/* If currency=BTC, show a "Proceeds (USD)" field */}
            {currency === "BTC" && (
              <div className="form-group">
                <label>Proceeds (USD):</label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  defaultValue={0}
                  {...register("proceeds_usd", { valueAsNumber: true })}
                />
              </div>
            )}

            {/* Warning if "Spent" but proceeds=0 */}
            {currency === "BTC" &&
              purposeVal === "Spent" &&
              proceedsUsdVal === 0 && (
                <div style={{ color: "red", marginTop: "5px" }}>
                  <strong>Warning:</strong> You selected “Spent” but “Proceeds (USD)” is 0.
                </div>
              )}
          </>
        );
      }

      case "Transfer": {
        const fromAccount = watch("fromAccount");
        const fromCurrencyVal = watch("fromCurrency");

        return (
          <>
            {/* From Account */}
            <div className="form-group">
              <label>From Account:</label>
              <select
                className="form-control"
                {...register("fromAccount", { required: true })}
              >
                <option value="">Select From Account</option>
                <option value="Bank">Bank Account</option>
                <option value="Wallet">Bitcoin Wallet</option>
                <option value="Exchange">Exchange</option>
              </select>
              {errors.fromAccount && (
                <span className="error-text">From Account is required</span>
              )}
            </div>

            {/* From Currency (auto-set if Bank/Wallet, user chooses if Exchange) */}
            <div className="form-group">
              <label>From Currency:</label>
              {fromAccount === "Exchange" ? (
                <select
                  className="form-control"
                  {...register("fromCurrency", { required: true })}
                >
                  <option value="">Select Currency</option>
                  <option value="USD">USD</option>
                  <option value="BTC">BTC</option>
                </select>
              ) : (
                <input
                  type="text"
                  className="form-control"
                  {...register("fromCurrency")}
                  readOnly
                />
              )}
              {errors.fromCurrency && (
                <span className="error-text">From Currency is required</span>
              )}
            </div>

            {/* Amount (From) */}
            <div className="form-group">
              <label>Amount (From):</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("amountFrom", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amountFrom && (
                <span className="error-text">Amount (From) is required</span>
              )}
            </div>

            {/* To Account (auto-set) */}
            <div className="form-group">
              <label>To Account:</label>
              <input
                type="text"
                className="form-control"
                {...register("toAccount")}
                readOnly
              />
            </div>

            {/* To Currency (auto-set) */}
            <div className="form-group">
              <label>To Currency:</label>
              <input
                type="text"
                className="form-control"
                {...register("toCurrency")}
                readOnly
              />
            </div>

            {/* Amount (To) */}
            <div className="form-group">
              <label>Amount (To):</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("amountTo", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amountTo && (
                <span className="error-text">Amount (To) is required</span>
              )}
            </div>

            {/* Fee: auto-calculated if BTC, manual if USD */}
            {fromCurrencyVal === "BTC" ? (
              <div className="form-group">
                <label>Fee (BTC):</label>
                <input
                  type="number"
                  step="0.00000001"
                  className="form-control"
                  {...register("fee", { valueAsNumber: true })}
                  readOnly
                />
                {feeInUsdDisplay > 0 && (
                  <small style={{ color: "#bbb" }}>
                    (~ ${feeInUsdDisplay} USD)
                  </small>
                )}
              </div>
            ) : (
              <div className="form-group">
                <label>Fee (USD):</label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  defaultValue={0}
                  {...register("fee", { valueAsNumber: true })}
                />
              </div>
            )}
          </>
        );
      }

      case "Buy":
        return (
          <>
            {/* Account always "Exchange" */}
            <div className="form-group">
              <label>Account:</label>
              <input
                type="text"
                className="form-control"
                value="Exchange"
                readOnly
                {...register("account")}
              />
            </div>

            {/* Amount USD */}
            <div className="form-group">
              <label>Amount USD:</label>
              <input
                type="number"
                step="0.01"
                className="form-control"
                {...register("amountUSD", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amountUSD && (
                <span className="error-text">Amount USD is required</span>
              )}
            </div>

            {/* Amount BTC */}
            <div className="form-group">
              <label>Amount BTC:</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("amountBTC", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amountBTC && (
                <span className="error-text">Amount BTC is required</span>
              )}
            </div>

            {/* Fee (USD) */}
            <div className="form-group">
              <label>Fee (USD):</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("fee", { valueAsNumber: true })}
              />
            </div>
          </>
        );

      case "Sell":
        return (
          <>
            {/* Account always "Exchange" */}
            <div className="form-group">
              <label>Account:</label>
              <input
                type="text"
                className="form-control"
                value="Exchange"
                readOnly
                {...register("account")}
              />
            </div>

            {/* Amount BTC */}
            <div className="form-group">
              <label>Amount BTC:</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("amountBTC", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amountBTC && (
                <span className="error-text">Amount BTC is required</span>
              )}
            </div>

            {/* Amount USD */}
            <div className="form-group">
              <label>Amount USD:</label>
              <input
                type="number"
                step="0.01"
                className="form-control"
                {...register("amountUSD", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
              {errors.amountUSD && (
                <span className="error-text">Amount USD is required</span>
              )}
            </div>

            {/* Fee (USD) */}
            <div className="form-group">
              <label>Fee (USD):</label>
              <input
                type="number"
                step="0.00000001"
                className="form-control"
                {...register("fee", { valueAsNumber: true })}
              />
            </div>
          </>
        );

      default:
        // If currentType is empty (user hasn't selected) or unknown
        return null;
    }
  };

  // ------------------------------------------------------------------------
  // Render the main form
  // ------------------------------------------------------------------------
  return (
    <form
      id={id || "transaction-form"}
      className="transaction-form"
      onSubmit={handleSubmit(onSubmit)}
    >
      <div className="form-fields-grid">
        {/* (1) Transaction Type dropdown */}
        <div className="form-group">
          <label>Transaction Type:</label>
          <select
            className="form-control"
            value={currentType}
            onChange={onTransactionTypeChange}
            required
          >
            <option value="">Select Transaction Type</option>
            <option value="Deposit">Deposit</option>
            <option value="Withdrawal">Withdrawal</option>
            <option value="Transfer">Transfer</option>
            <option value="Buy">Buy</option>
            <option value="Sell">Sell</option>
          </select>
        </div>

        {/* (2) Date & Time input */}
        <div className="form-group">
          <label>Date & Time:</label>
          <input
            type="datetime-local"
            className="form-control"
            {...register("timestamp", { required: "Date & Time is required" })}
          />
          {errors.timestamp && (
            <span className="error-text">{errors.timestamp.message}</span>
          )}
        </div>

        {/* (3) Dynamic fields for each transaction type */}
        {renderDynamicFields()}
      </div>
    </form>
  );
};

export default TransactionForm;

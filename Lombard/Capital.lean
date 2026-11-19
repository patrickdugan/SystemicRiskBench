/-
SRB-LOMBARD-01. Rational arithmetic proofs for Bagehot's worked merchant
example and an explicitly stipulated two-ledger rescue accounting model.

Proof boundaries:
* The higher leveraged ROE theorem assumes identical operating asset returns,
  equal asset capital, positive equity and debt, and debt interest below ROA.
* The converse theorem proves how a bad funding spread defeats that advantage.
* Central-bank lending creates an asset and an equal liability at origination.
  Capital injections and post-lending losses are distinct accounting operations.
* Repeated recap is a conditional recurrence, not proof of endemic crises.
All quantities are abstract accounting units; no real-policy claim is proved.
-/
import Mathlib

namespace Lombard

def merchantROE (gross rate debt equity : ℚ) : ℚ :=
  (gross - rate * debt) / equity

def unleveredROE (gross assets : ℚ) : ℚ :=
  gross / assets

/-- Debt-funded capital increases ROE if the operating return exceeds the debt rate. -/
theorem leveraged_roe_gt_if_positive_spread
    {assets equity debt gross rate : ℚ}
    (hassets : assets = equity + debt)
    (hequity : 0 < equity)
    (hdebt : 0 < debt)
    (hspread : rate * assets < gross) :
    unleveredROE gross assets < merchantROE gross rate debt equity := by
  have hassetspos : 0 < assets := by
    rw [hassets]
    linarith
  have hprod : 0 < debt * (gross - rate * assets) :=
    mul_pos hdebt (sub_pos.mpr hspread)
  have hidentity : (gross - rate * debt) * assets - gross * equity =
      debt * (gross - rate * assets) := by
    rw [hassets]
    ring
  unfold unleveredROE merchantROE
  apply (div_lt_div_iff₀ hassetspos hequity).2
  linarith

/-- When funding costs exceed gross asset return, leverage reverses the ranking. -/
theorem leveraged_roe_lt_if_negative_spread
    {assets equity debt gross rate : ℚ}
    (hassets : assets = equity + debt)
    (hequity : 0 < equity)
    (hdebt : 0 < debt)
    (hspread : gross < rate * assets) :
    merchantROE gross rate debt equity < unleveredROE gross assets := by
  have hassetspos : 0 < assets := by
    rw [hassets]
    linarith
  have hprod : 0 < debt * (rate * assets - gross) :=
    mul_pos hdebt (sub_pos.mpr hspread)
  have hidentity : gross * equity - (gross - rate * debt) * assets =
      debt * (rate * assets - gross) := by
    rw [hassets]
    ring
  unfold unleveredROE merchantROE
  apply (div_lt_div_iff₀ hequity hassetspos).2
  linarith

/-- Holding volume and all other costs fixed, a bounded price cut preserves
    a stipulated target equity return. -/
theorem price_cut_preserves_equity_target
    {gross rate debt equity cut target : ℚ}
    (hequity : 0 < equity)
    (hbudget : cut ≤ gross - rate * debt - target * equity) :
    target ≤ merchantROE (gross - cut) rate debt equity := by
  unfold merchantROE
  apply (le_div_iff₀ hequity).2
  linarith

/-- £50,000 cash merchant: £5,000 operating surplus / £50,000 own capital. -/
theorem bagehot_cash_roe :
    unleveredROE (5000 : ℚ) 50000 = 1 / 10 := by
  norm_num [unleveredROE]

/-- £10,000 equity plus £40,000 debt at 5%; borrower ROE is 30%. -/
theorem bagehot_borrower_roe :
    merchantROE (5000 : ℚ) (1 / 20) 40000 10000 = 3 / 10 := by
  norm_num [merchantROE]

/-- Given a 10% target on £10,000 equity, annual price-cut slack is £2,000. -/
theorem bagehot_annual_price_cut_budget :
    (5000 : ℚ) - (1 / 20) * 40000 - (1 / 10) * 10000 = 2000 := by
  norm_num

/-- Book common equity is assets less contractual debts. -/
def bookEquity (assets liabilities : ℚ) : ℚ := assets - liabilities

/-- Collateralized emergency lending increases cash and debt equally, with
    book equity unchanged at origination before any impairment. -/
theorem emergency_liquidity_not_recapitalization
    (assets liabilities loan : ℚ) :
    bookEquity (assets + loan) (liabilities + loan) =
      bookEquity assets liabilities := by
  simp only [bookEquity]
  ring

/-- Recognizing a credit loss consumes the bank's equity. -/
theorem credit_loss_reduces_book_equity
    (assets liabilities loss : ℚ) :
    bookEquity (assets - loss) liabilities =
      bookEquity assets liabilities - loss := by
  simp only [bookEquity]
  ring

/-- Paid-in equity makes the receiving bank's book equity rise by that amount. -/
theorem bank_equity_injection
    (assets liabilities loss recap : ℚ) :
    bookEquity (assets - loss + recap) liabilities =
      bookEquity assets liabilities - loss + recap := by
  simp only [bookEquity]
  ring

/-- If an initially capital-compliant bank suffers a loss, an exactly
    loss-matched equity injection restores its original compliance condition
    under book-value accounting. -/
theorem matched_recap_preserves_capital_floor
    {assets equity loss ratio : ℚ}
    (hinitial : ratio * assets ≤ equity) :
    ratio * (assets - loss + loss) ≤ equity - loss + loss := by
  calc
    ratio * (assets - loss + loss) = ratio * assets := by ring
    _ ≤ equity := hinitial
    _ = equity - loss + loss := by ring

/-- An initially binding equity ratio fails after a positive loss when 0 < k < 1
    and assets shrink by the amount of the loss. -/
theorem binding_capital_breached_after_loss
    {assets equity loss ratio : ℚ}
    (hbinding : ratio * assets = equity)
    (hloss : 0 < loss)
    (hratio : ratio < 1) :
    equity - loss < ratio * (assets - loss) := by
  have hprod : 0 < (1 - ratio) * loss :=
    mul_pos (by linarith) hloss
  nlinarith

/-- Regulatory equity/risk-asset ratio bound for a simplified unit-risk book. -/
theorem capital_ratio_implies_capacity_bound
    {assets equity ratio : ℚ}
    (hpositive : 0 < ratio)
    (hcapital : ratio * assets ≤ equity) :
    assets ≤ equity / ratio := by
  apply (le_div_iff₀ hpositive).2
  simpa [mul_comm] using hcapital

/-- A loss-recognizing central bank needs an explicit fiscal transfer to
    restore the book equity target; creating reserves is another transaction. -/
theorem central_bank_loss_and_fiscal_recap
    (cbAssets cbLiabilities loss treasuryTransfer : ℚ) :
    bookEquity (cbAssets - loss + treasuryTransfer) cbLiabilities =
      bookEquity cbAssets cbLiabilities - loss + treasuryTransfer := by
  simp only [bookEquity]
  ring

/-- A three-period conditional illustration: losses and matching transfers. -/
def rescuedEquity (initial loss : ℚ) : ℕ → ℚ
  | 0 => initial
  | n + 1 => rescuedEquity initial loss n - loss + loss

def cumulativeTransfers (loss : ℚ) : ℕ → ℚ
  | 0 => 0
  | n + 1 => cumulativeTransfers loss n + loss

theorem loss_matched_recap_repeats_unchanged
    (initial loss : ℚ) (n : ℕ) :
    rescuedEquity initial loss n = initial := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp [rescuedEquity, ih]

theorem public_transfers_are_number_of_rounds_times_loss
    (loss : ℚ) (n : ℕ) :
    cumulativeTransfers loss n = (n : ℚ) * loss := by
  induction n with
  | zero => simp [cumulativeTransfers]
  | succ n ih =>
      simp only [cumulativeTransfers, ih, Nat.cast_add, Nat.cast_one]
      ring

theorem bagehot_synthetic_bank_loss :
    bookEquity ((500 : ℚ) - 30) 450 = 20 := by
  norm_num [bookEquity]

theorem bagehot_synthetic_bank_liquidity_unchanged :
    bookEquity (((500 : ℚ) - 30) + 30) (450 + 30) = 20 := by
  norm_num [bookEquity]

theorem bagehot_three_period_public_cost :
    cumulativeTransfers 30 3 = (90 : ℚ) := by
  norm_num [public_transfers_are_number_of_rounds_times_loss]

theorem central_bank_loss_requires_four_if_restored :
    bookEquity ((10 : ℚ) - 4 + 4) 0 = 10 := by
  norm_num [bookEquity]

#print axioms leveraged_roe_gt_if_positive_spread
#print axioms leveraged_roe_lt_if_negative_spread
#print axioms binding_capital_breached_after_loss
#print axioms loss_matched_recap_repeats_unchanged
#print axioms public_transfers_are_number_of_rounds_times_loss

end Lombard

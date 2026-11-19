/-
SRB-LOMBARD-02. Exact one-period pricing identities for an assumed Treasury
guarantee of bank-debt creditor shortfall.

The guarantee is a new post-1873 policy assumption. These proofs cover
contractual expected creditor receipts and comparative statics, while the
Python experiment enumerates merchant project/debt best responses. This
file makes no empirical or policy-welfare statement.
-/
import Mathlib

namespace Lombard.Funding

/-- hazard = bank failure probability * conditional bank-creditor loss fraction.
    Risk-free gross promised return is 1+rf. -/
def bankRate (rf hazard coverage : ℚ) : ℚ :=
  (1+rf)/(1-hazard*(1-coverage))-1

/-- A competitive creditor has the stipulated break-even expected return. -/
theorem bank_funding_parity
    {rf hazard coverage : ℚ}
    (hden : 0 < 1-hazard*(1-coverage)) :
    (1+bankRate rf hazard coverage) * (1-hazard*(1-coverage)) =
       1+rf := by
  dsimp [bankRate]
  field_simp [ne_of_gt hden]

/-- If bank default/LGD risk is held fixed and the guarantee rises, its
    actuarially fair promised bank funding rate weakly decreases. -/
theorem more_guarantee_lowers_bank_rate
    {rf hazard g₀ g₁ : ℚ}
    (hbase : 0 < 1+rf)
    (hhaz : 0 ≤ hazard)
    (hhazUpper : hazard < 1)
    (hg₀ : 0 ≤ g₀)
    (horder : g₀ ≤ g₁)
    (hg₁ : g₁ ≤ 1) :
    bankRate rf hazard g₁ ≤ bankRate rf hazard g₀ := by
  have hgt₀ : 1-g₀ ≤ 1 := by linarith
  have hgt₁ : 1-g₁ ≤ 1 := by linarith
  have hle₀ : hazard*(1-g₀) ≤ hazard := by
    have h := mul_le_mul_of_nonneg_left hgt₀ hhaz
    nlinarith
  have hle₁ : hazard*(1-g₁) ≤ hazard := by
    have h := mul_le_mul_of_nonneg_left hgt₁ hhaz
    nlinarith
  have hden₀ : 0 < 1-hazard*(1-g₀) := by linarith
  have hden₁ : 0 < 1-hazard*(1-g₁) := by linarith
  have hdenOrder : 1-hazard*(1-g₀) ≤ 1-hazard*(1-g₁) := by
    have h := mul_le_mul_of_nonneg_left (show 1-g₁ ≤ 1-g₀ by linarith) hhaz
    linarith
  have hfrac :
      (1+rf)/(1-hazard*(1-g₁)) ≤ (1+rf)/(1-hazard*(1-g₀)) := by
    apply (div_le_div_iff₀ hden₁ hden₀).2
    exact mul_le_mul_of_nonneg_left hdenOrder (le_of_lt hbase)
  dsimp [bankRate]
  linarith

/-- If credit risk is zero, coverage provides no bank financing discount. -/
theorem zero_bank_default_risk_implies_no_discount
    (rf coverage : ℚ) :
    bankRate rf 0 coverage = rf := by
  simp [bankRate]

def passedRate (unbacked backed alpha : ℚ) : ℚ :=
  unbacked-alpha*(unbacked-backed)

/-- Funding subsidies do not reach borrowers when intermediary pass-through
    is zero. -/
theorem zero_pass_through_no_merchant_subsidy
    (unbacked backed : ℚ) :
    passedRate unbacked backed 0 = unbacked := by
  simp [passedRate]

theorem full_pass_through
    (unbacked backed : ℚ) :
    passedRate unbacked backed 1 = backed := by
  simp [passedRate]
  ring

/-- Increasing a stipulated pass-through fraction reduces the merchant's
    bank-base funding charge when a lower backed rate exists. -/
theorem more_pass_through_lowers_merchant_base_rate
    {unbacked backed a₀ a₁ : ℚ}
    (hsaving : backed ≤ unbacked)
    (halpha : a₀ ≤ a₁) :
    passedRate unbacked backed a₁ ≤
      passedRate unbacked backed a₀ := by
  dsimp [passedRate]
  have hs : 0 ≤ unbacked-backed := sub_nonneg.mpr hsaving
  have hm := mul_le_mul_of_nonneg_right halpha hs
  linarith

/-- Cost of merchant debt at default-loss hazard p*(1-recovery), assuming
    complete repayment in the project success state. -/
def merchantRate (bankBase originationMargin merchantHazard : ℚ) : ℚ :=
  (1+bankBase+originationMargin)/(1-merchantHazard)-1

theorem lower_bank_base_lowers_merchant_rate
    {lo hi margin hazard : ℚ}
    (hlo : lo ≤ hi)
    (hden : 0 < 1-hazard) :
    merchantRate lo margin hazard ≤ merchantRate hi margin hazard := by
  have hfrac :
      (1+lo+margin)/(1-hazard) ≤ (1+hi+margin)/(1-hazard) := by
    apply (div_le_div_iff₀ hden hden).2
    exact mul_le_mul_of_nonneg_right (by linarith) (le_of_lt hden)
  dsimp [merchantRate]
  linarith

/-- Synthetic bank-default probability sensitivity to aggregate risky lending.
    All causal content sits in this chosen linear function. -/
def linkedBankDefault (base slope merchantPD debtToEquity : ℚ) : ℚ :=
  base+slope*merchantPD*debtToEquity

theorem linked_bank_pd_nondecreasing_in_leverage
    {base slope merchantPD lowerDebt higherDebt : ℚ}
    (hslope : 0 ≤ slope)
    (hmerchant : 0 ≤ merchantPD)
    (hdebt : lowerDebt ≤ higherDebt) :
    linkedBankDefault base slope merchantPD lowerDebt ≤
      linkedBankDefault base slope merchantPD higherDebt := by
  dsimp [linkedBankDefault]
  have hprod : 0 ≤ slope*merchantPD := mul_nonneg hslope hmerchant
  have hm := mul_le_mul_of_nonneg_left hdebt hprod
  nlinarith

/-- Expected Treasury payout for a fixed bank funding face is contingent on
    bank default and the promised percentage of the creditor shortfall. -/
def treasuryExpected (bankPD coverage lossFraction promisedFace : ℚ) : ℚ :=
  bankPD*coverage*lossFraction*promisedFace

theorem zero_coverage_zero_expected_treasury
    (pd lossFraction face : ℚ) :
    treasuryExpected pd 0 lossFraction face = 0 := by
  simp [treasuryExpected]

/-- For a fixed bank face, PD and LGD, greater coverage entails weakly
    higher government expected payout. The promised face itself changes in
    the Python counterfactual, so this is a partial-equilibrium proposition. -/
theorem more_coverage_more_treasury_at_fixed_face
    {pd lgd face g₀ g₁ : ℚ}
    (hpd : 0 ≤ pd) (hlgd : 0 ≤ lgd) (hface : 0 ≤ face)
    (horder : g₀ ≤ g₁) :
    treasuryExpected pd g₀ lgd face ≤ treasuryExpected pd g₁ lgd face := by
  dsimp [treasuryExpected]
  have hprod : 0 ≤ pd*lgd*face := by positivity
  have hm := mul_le_mul_of_nonneg_left horder hprod
  nlinarith

#print axioms bank_funding_parity
#print axioms more_guarantee_lowers_bank_rate
#print axioms zero_pass_through_no_merchant_subsidy
#print axioms more_pass_through_lowers_merchant_base_rate
#print axioms lower_bank_base_lowers_merchant_rate
#print axioms linked_bank_pd_nondecreasing_in_leverage
#print axioms more_coverage_more_treasury_at_fixed_face

end Lombard.Funding

use anchor_lang::prelude::*;
#[error_code]
pub enum RecoveredError {
    #[msg("Invalid carry basis")]
    Init_InvalidCarryBasis = 0,
    #[msg("Invalid fee authority")]
    InvalidFeeAuthority = 1,
    #[msg("Fundraise must be finalized")]
    InitCurve_FundraiseNotFinalized = 2,
    #[msg("Curve already initialized")]
    InitCurve_AlreadyInitialized = 3,
    #[msg("Redemption not started")]
    Redeem_NotStarted = 4,
    #[msg("Redemption already started")]
    Redeem_AlreadyStarted = 5,
    #[msg("User redeemed more than they have")]
    Redeem_ExceedOwned = 6,
    #[msg("Fund is not expired")]
    Redeem_FundNotExpired = 7,
    #[msg("No more delegate authorities allowed")]
    Delegate_ExceededMax = 8,
    #[msg("Authority not found")]
    Delegate_AuthorityNotFound = 9,
    #[msg("Authority already exists")]
    Delegate_DuplicateAuthority = 10,
    #[msg("Unauthorized")]
    Unauthorized = 11,
    #[msg("Fund is expired")]
    Execute_FundExpired = 12,
    #[msg("Fund is closed")]
    Execute_FundClosed = 13,
    #[msg("Cannot start raise twice")]
    StartRaise_InvalidState = 14,
    #[msg("Funding duration exceeds max")]
    StartRaise_FundingDurationExceedsMax = 15,
    #[msg("Vesting amount mismatch")]
    StartRaise_VestingAmountMismatch = 16,
    #[msg("Curve not initialized")]
    StartVest_CurveNotInitialized = 17,
    #[msg("Vesting already started")]
    StartVest_AlreadyStarted = 18,
    #[msg("LP mint already initialized")]
    InitCurveLp_AlreadyInitialized = 19,
    #[msg("Unexpected state")]
    UnexpectedState = 20,
    #[msg("Too high sniping amount")]
    TooHighSnipingAmount = 21,
    #[msg("Invalid wallet token ATA")]
    InvalidWalletTokenATA = 22,
    #[msg("Curve already deactivated")]
    CurveAlreadyDeactivated = 23,
}

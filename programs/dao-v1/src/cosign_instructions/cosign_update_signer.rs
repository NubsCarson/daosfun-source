use crate::*;
#[derive(Accounts)]
pub struct CosignUpdateSigner<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,
    #[account(constraint = admin.key() == CLOSE_AUTHORITY @ RecoveredError::Unauthorized)]
    pub admin: Signer<'info>,
    #[account(mut)]
    pub state: Account<'info, CosignState>,
}

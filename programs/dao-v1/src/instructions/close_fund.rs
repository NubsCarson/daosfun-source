use crate::*;
#[derive(Accounts)]
pub struct CloseFund<'info> {
    #[account(mut, constraint = admin.key() == CLOSE_AUTHORITY @ RecoveredError::Unauthorized)]
    pub admin: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    #[account(mut, seeds = [b"state", dao_mint.key().as_ref()], bump, constraint = state.dao_mint == dao_mint.key())]
    pub state: Account<'info, State>,
}

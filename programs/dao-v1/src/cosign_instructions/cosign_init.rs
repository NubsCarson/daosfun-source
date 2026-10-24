use crate::*;











#[derive(Accounts)]
#[instruction(id: u8)]
pub struct CosignInit<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,
    #[account(constraint = admin.key() == CLOSE_AUTHORITY @ RecoveredError::Unauthorized)]
    pub admin: Signer<'info>,
    #[account(init, payer = payer, space = 41, seeds = [b"cosigner".as_ref(), &[id]], bump)]
    pub cosign_state: Account<'info, CosignState>,
    pub system_program: Program<'info, System>,
}

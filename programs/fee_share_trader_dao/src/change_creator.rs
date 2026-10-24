use anchor_lang::prelude::*;
use crate::state::FeeShareState;

pub const OPERATOR: Pubkey = Pubkey::new_from_array([
    0x52,0x95,0x82,0x69,0xd2,0xc3,0x18,0xe5,0x11,0x3c,0x2d,0xaa,0xb9,0x5f,0x48,0xa2,
    0x0b,0x23,0xc6,0x84,0x13,0x10,0x18,0xe8,0x9c,0xfc,0xda,0xa8,0x01,0x58,0xda,0xf4,
]);

// Recovered from the captured fee-share executable and local VM probes.
#[derive(Accounts)]
pub struct ChangeCreator<'info> {
    #[account(constraint = signer.key() == OPERATOR @ ChangeCreatorError::Unauthorized)]
    pub signer: Signer<'info>,
    /// CHECK: Only the key is used, with no owner or signer constraint.
    pub new_creator: UncheckedAccount<'info>,
    #[account(mut)]
    pub fee_share_state: Account<'info, FeeShareState>,
}

pub fn handle_change_creator(ctx: Context<ChangeCreator>) -> Result<()> {
    ctx.accounts.fee_share_state.creator = ctx.accounts.new_creator.key();
    Ok(())
}

#[error_code]
pub enum ChangeCreatorError {
    #[msg("Unauthorized")]
    Unauthorized = 1,
}

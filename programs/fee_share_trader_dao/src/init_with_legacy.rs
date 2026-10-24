use anchor_lang::prelude::*;
use anchor_spl::token_interface::Mint;
use crate::state::FeeShareState;
pub const LEGACY_PROGRAM: Pubkey = Pubkey::new_from_array([116, 104, 192, 252, 75, 213, 165, 80, 1, 239, 139, 250, 23, 229, 5, 187, 77, 41, 5, 61, 90, 157, 177, 207, 68, 162, 37, 88, 46, 235, 224, 242]);
#[derive(Accounts)]
pub struct InitWithLegacy<'info> {
 #[account(mut)] pub payer: Signer<'info>,
 pub token_mint: InterfaceAccount<'info, Mint>,
 /// CHECK: Explicit legacy PDA, exact length and discriminator checked below.
 #[account(seeds = [b"fee_share_state", token_mint.key().as_ref()], bump, seeds::program = LEGACY_PROGRAM)]
 pub legacy_fee_share_state: UncheckedAccount<'info>,
 #[account(init, payer = payer, space = 169, seeds = [b"fee_share_state", token_mint.key().as_ref()], bump)]
 pub fee_share_state: Account<'info, FeeShareState>,
 pub system_program: Program<'info, System>,
}
#[derive(AnchorDeserialize)]
pub struct LegacyState {
 pub total_fees: u64, pub funding_mint: Pubkey, pub creator: Pubkey,
 pub referrer: Pubkey, pub platform: Pubkey,
 pub creator_distributed: u64, pub referrer_distributed: u64, pub platform_distributed: u64,
}
pub fn handle_init_with_legacy(ctx: Context<InitWithLegacy>) -> Result<()> {
 let data = ctx.accounts.legacy_fee_share_state.try_borrow_data()?;
 require!(data.len() == 168, LegacyError::LegacyStateInvalid);
 require!(data[..8] == [38,195,84,207,192,143,5,68], LegacyError::LegacyStateInvalid);
 let old = LegacyStateAccount::deserialize(&data).map_err(|_| error!(LegacyError::LegacyStateInvalid))?.0;
 let state = &mut ctx.accounts.fee_share_state;
 state.funding_mint = old.funding_mint;
 state.dao_mint = ctx.accounts.token_mint.key();
 state.creator = old.creator;
 state.referrer = Some(old.referrer);
 Ok(())
}
#[error_code]
pub enum LegacyError {
 #[msg("Legacy fee share state is not valid.")]
 LegacyStateInvalid = 3,
}

// Decoder structure retained from the saved legacy SDK, behind the observed checks.
pub struct LegacyStateAccount(pub LegacyState);
impl LegacyStateAccount {
 pub fn deserialize(buf: &[u8]) -> std::io::Result<Self> {
  use std::io::Read;
  let mut reader = buf;
  let mut discriminator = [0u8; 8];
  reader.read_exact(&mut discriminator)?;
  let expected = [38,195,84,207,192,143,5,68];
  if discriminator != expected {
   return Err(std::io::Error::new(std::io::ErrorKind::Other,
    format!("discm does not match. Expected: {:?}. Received: {:?}", expected, discriminator)));
  }
  Ok(Self(LegacyState::deserialize(&mut reader)?))
 }
}

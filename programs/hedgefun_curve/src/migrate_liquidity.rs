use anchor_lang::prelude::*;
use anchor_spl::{associated_token::AssociatedToken, token_interface::{self, Mint, TokenAccount, TokenInterface, TransferChecked}};
use crate::state::curve::HedgefunCurve;

#[derive(Accounts)]
pub struct MigrateLiquidity<'info> {
 pub signer: Signer<'info>,
 pub depositor: Signer<'info>,
 pub token_mint: InterfaceAccount<'info, Mint>,
 pub funding_mint: InterfaceAccount<'info, Mint>,
 #[account(mut, seeds = [b"curve", depositor.key().as_ref()], bump,
  constraint = curve.token_mint == token_mint.key() @ MigrationError::InvalidMint,
  constraint = curve.funding_mint == funding_mint.key() @ MigrationError::InvalidMint,
  constraint = !curve.migrated @ MigrationError::AlreadyMigrated,
  constraint = curve.complete)]
 pub curve: Account<'info, HedgefunCurve>,
 #[account(mut, token::mint = funding_mint, token::authority = signer, token::token_program = funding_token_program)]
 pub signer_funding_ata: InterfaceAccount<'info, TokenAccount>,
 #[account(mut, associated_token::mint = funding_mint, associated_token::authority = curve, associated_token::token_program = funding_token_program)]
 pub funding_vault: InterfaceAccount<'info, TokenAccount>,
 pub funding_token_program: Interface<'info, TokenInterface>,
 pub associated_token_program: Program<'info, AssociatedToken>,
}

pub fn handle_migrate_liquidity(ctx: Context<MigrateLiquidity>) -> Result<()> {
 let depositor = ctx.accounts.depositor.key();
 let seeds: &[&[u8]] = &[b"curve", depositor.as_ref(), &[ctx.bumps.curve]];
 token_interface::transfer_checked(CpiContext::new_with_signer(ctx.accounts.funding_token_program.to_account_info(), TransferChecked {
  from: ctx.accounts.funding_vault.to_account_info(), mint: ctx.accounts.funding_mint.to_account_info(),
  to: ctx.accounts.signer_funding_ata.to_account_info(), authority: ctx.accounts.curve.to_account_info(),
 }, &[seeds]), ctx.accounts.curve.funding_amount, ctx.accounts.funding_mint.decimals)?;
 ctx.accounts.curve.migrated = true;
 Ok(())
}

#[error_code]
pub enum MigrationError {
 #[msg("Invalid Mint")]
 InvalidMint = 1,
 #[msg("Already Migrated")]
 AlreadyMigrated = 5,
}

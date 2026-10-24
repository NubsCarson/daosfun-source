use crate::*;
impl<'info> TransferPositionNftToFeeShare<'info> {
    #[inline(never)]
    pub fn transfer_nft_context(&self) -> CpiContext<'_, '_, '_, 'info, anchor_spl::token_interface::SetAuthority<'info>> {
        let cpi_program = self.token_2022_program.to_account_info();
        let cpi_accounts = anchor_spl::token_interface::SetAuthority {
            current_authority: self.meteora_authority.to_account_info(),
            account_or_mint: self.position_nft_account.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

#[derive(Accounts)]
pub struct TransferPositionNftToFeeShare<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub token_mint: Box<InterfaceAccount<'info, Mint>>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(seeds = [b"state", token_mint.key().as_ref()], bump,
        constraint = state.dao_mint == token_mint.key() && state.funding_mint == funding_mint.key() @ RecoveredError::Unauthorized)]
    pub state: Box<Account<'info, State>>,
    #[account(constraint = pool.load()?.token_a_mint == token_mint.key()
        && pool.load()?.token_b_mint == funding_mint.key() @ RecoveredError::Unauthorized)]
    pub pool: AccountLoader<'info, ExternalPool>,
    /// CHECK: Used to derive the position and NFT account; no mint parsing in the original.
    pub position_nft_mint: UncheckedAccount<'info>,
    /// CHECK: PDA checked here; Token-2022 validates the account for SetAuthority.
    #[account(mut, seeds = [b"position_nft_account", position_nft_mint.key().as_ref()], bump, seeds::program = AMM_PROGRAM)]
    pub position_nft_account: UncheckedAccount<'info>,
    #[account(seeds = [b"position", position_nft_mint.key().as_ref()], bump, seeds::program = AMM_PROGRAM,
        constraint = position.load()?.pool == pool.key() @ RecoveredError::Unauthorized)]
    pub position: AccountLoader<'info, ExternalPosition>,
    /// CHECK: Global PDA signs the token ownership change.
    #[account(seeds = [b"meteora_authority"], bump)]
    pub meteora_authority: UncheckedAccount<'info>,
    #[account(seeds = [b"fee_share_state", token_mint.key().as_ref()], bump, seeds::program = fee_share_trader_dao::ID,
        constraint = funding_mint.key() == fee_authority.funding_mint && token_mint.key() == fee_authority.dao_mint)]
    pub fee_authority: Box<Account<'info, FeeShareState>>,
    pub token_2022_program: Program<'info, anchor_spl::token_2022::Token2022>,
}

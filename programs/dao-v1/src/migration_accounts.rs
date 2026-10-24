use crate::*;
pub const HEDGE_PROGRAM: Pubkey = pubkey!("HedgENAip7ZEzRj6T3ZbY1PmDFXU5XKx1BFSKbxvVD7V");

// Field labels outside the mint identities and reserves are inferred. The
// trailing region is retained as opaque bytes because the target does not use it.
pub use hedgefun_curve::state::curve::HedgefunCurve as HedgefunCurve;

#[derive(Accounts)]
pub struct MigrateBondingToMeteora<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    pub token_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(mut, seeds = [b"state", token_mint.key().as_ref()], bump,
        constraint = state.dao_mint == token_mint.key() && state.funding_mint == funding_mint.key() @ RecoveredError::Unauthorized,
        constraint = state.curve_initialized == false @ RecoveredError::InitCurve_AlreadyInitialized)]
    pub state: Box<Account<'info, State>>,
    #[account(mut, seeds = [b"curve", state.key().as_ref()], bump, seeds::program = hedgefun_curve::ID,
        constraint = hedgefun_curve.token_mint == token_mint.key() && hedgefun_curve.funding_mint == funding_mint.key() @ RecoveredError::UnexpectedState)]
    pub hedgefun_curve: Box<Account<'info, HedgefunCurve>>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = hedgefun_curve, associated_token::token_program = funding_token_program)]
    pub curve_funding_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, seeds = [b"wallet", token_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = wallet, associated_token::token_program = funding_token_program)]
    pub wallet_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = token_mint, associated_token::authority = payer, associated_token::token_program = dao_token_program)]
    pub payer_token_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = payer, associated_token::token_program = funding_token_program)]
    pub payer_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = token_mint, associated_token::authority = state, associated_token::token_program = dao_token_program)]
    pub state_token_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: Validated and created by DAMM.
    #[account(mut, seeds = [b"token_vault", token_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = amm_program.key())]
    pub pool_token_vault: UncheckedAccount<'info>,
    /// CHECK: Validated and created by DAMM.
    #[account(mut, seeds = [b"token_vault", funding_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = amm_program.key())]
    pub pool_funding_vault: UncheckedAccount<'info>,
    #[account(seeds = [b"fee_share_state", token_mint.key().as_ref()], bump, seeds::program = fee_share_trader_dao::ID,
        constraint = funding_mint.key() == fee_authority.funding_mint && token_mint.key() == fee_authority.dao_mint)]
    pub fee_authority: Box<Account<'info, FeeShareState>>,
    /// CHECK: Legacy fee token account, not parsed by target.
    #[account(mut)]
    pub fee_nft_account: UncheckedAccount<'info>,
    /// CHECK: Program payer.
    #[account(mut, seeds = [b"meteora_authority"], bump)]
    pub meteora_authority: UncheckedAccount<'info>,
    #[account(address = DAMM_CONFIG)]
    pub pool_config: AccountLoader<'info, ExternalDammConfig>,
    /// CHECK: DAMM authority.
    #[account(seeds = [b"pool_authority"], bump, seeds::program = AMM_PROGRAM)]
    pub pool_authority: UncheckedAccount<'info>,
    /// CHECK: DAMM validates and initializes the pool.
    #[account(mut)]
    pub pool: UncheckedAccount<'info>,
    /// CHECK: Program-derived mint is created by DAMM.
    #[account(mut, seeds = [b"position_nft_mint", token_mint.key().as_ref()], bump)]
    pub position_nft_mint: UncheckedAccount<'info>,
    /// CHECK: DAMM NFT account.
    #[account(mut, seeds = [b"position_nft_account", position_nft_mint.key().as_ref()], bump, seeds::program = AMM_PROGRAM)]
    pub position_nft_account: UncheckedAccount<'info>,
    /// CHECK: DAMM position account.
    #[account(mut, seeds = [b"position", position_nft_mint.key().as_ref()], bump, seeds::program = AMM_PROGRAM)]
    pub position: UncheckedAccount<'info>,
    /// CHECK: DAMM event authority.
    #[account(seeds = [b"__event_authority"], bump, seeds::program = AMM_PROGRAM)]
    pub damm_event_authority: UncheckedAccount<'info>,
    /// CHECK: Legacy curve program identity.
    pub hedgefun_curve_program: Program<'info, hedgefun_curve::program::HedgefunCurve>,
    pub token_2022_program: Program<'info, anchor_spl::token_2022::Token2022>,
    pub dao_token_program: Interface<'info, TokenInterface>,
    pub funding_token_program: Interface<'info, TokenInterface>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
    /// CHECK: External executable identity.
    pub amm_program: Program<'info, DammProgram>,
}

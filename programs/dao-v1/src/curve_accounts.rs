//! Account interface recovered from the deployed InitCurve parser.
use crate::*;
pub const DAMM_CONFIG: Pubkey = pubkey!("CtnY6H6AYJJ3WxN5MSY2NQAqrzPY4qTW1gb5ySzvPhaE");

#[repr(C)]
#[derive(Clone, Copy, AnchorSerialize, AnchorDeserialize, bytemuck::Pod, bytemuck::Zeroable)]
pub struct ExternalDammConfig {
    pub data: [u64; 40],
}
impl anchor_lang::ZeroCopy for ExternalDammConfig {}
impl Owner for ExternalDammConfig {
    fn owner() -> Pubkey {
        AMM_PROGRAM
    }
}
impl Discriminator for ExternalDammConfig {
    const DISCRIMINATOR: [u8; 8] = [155, 12, 170, 224, 30, 250, 204, 130];
}
pub use fee_share_trader_dao::state::FeeShareState as FeeShareState;
pub use fundraise::state::fundraise::FundraiseState as ExternalFundraiseState;

#[derive(Accounts)]
pub struct InitCurve<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    pub token_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(mut, seeds = [b"state", token_mint.key().as_ref()], bump,
        constraint = state.dao_mint == token_mint.key() @ RecoveredError::Unauthorized, constraint = state.funding_mint == funding_mint.key() @ RecoveredError::Unauthorized,
        constraint = state.curve_initialized == false @ RecoveredError::InitCurve_AlreadyInitialized)]
    pub state: Box<Account<'info, State>>,
    #[account(constraint = check_curve_pda(&fundraise_state.key(), &FUNDRAISE_PROGRAM, &[b"fundraise", state.key().as_ref(), token_mint.key().as_ref()]) @ RecoveredError::Unauthorized, constraint = fundraise_state.is_finalized @ RecoveredError::Unauthorized)]
    pub fundraise_state: Box<Account<'info, ExternalFundraiseState>>,
    #[account(mut, seeds = [b"wallet", token_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = wallet, associated_token::token_program = funding_token_program)]
    pub wallet_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = token_mint, associated_token::authority = state, associated_token::token_program = dao_token_program)]
    pub state_token_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = state, associated_token::token_program = funding_token_program)]
    pub state_funding_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = token_mint, associated_token::authority = signer, associated_token::token_program = dao_token_program)]
    pub signer_token_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = signer, associated_token::token_program = funding_token_program)]
    pub signer_funding_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: Legacy fee mint address only.
    #[account(mut, seeds = [b"fee_nft_mint", token_mint.key().as_ref()], bump)]
    pub fee_nft_mint: UncheckedAccount<'info>,
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
    /// CHECK: Program signer.
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
    pub token_2022_program: Program<'info, anchor_spl::token_2022::Token2022>,
    pub dao_token_program: Interface<'info, TokenInterface>,
    pub funding_token_program: Interface<'info, TokenInterface>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
    /// CHECK: External executable identity.
    
    pub amm_program: Program<'info, DammProgram>,
}

#[inline(always)]
fn fundraise_address(state: Pubkey, mint: Pubkey) -> Pubkey {
    Pubkey::find_program_address(
        &[b"fundraise", state.as_ref(), mint.as_ref()],
        &FUNDRAISE_PROGRAM,
    )
    .0
}

#[inline(never)]
pub(crate) fn check_curve_ata(
    account: &InterfaceAccount<TokenAccount>,
    mint: Pubkey,
    owner: Pubkey,
    token: Pubkey,
) -> Result<bool> {
    use anchor_lang::error::ErrorCode;
    if account.to_account_info().owner != &token {
        return Err(ErrorCode::ConstraintAssociatedTokenTokenProgram.into());
    }
    if account.owner != owner {
        return Err(ErrorCode::ConstraintTokenOwner.into());
    }
    if account.key()
        != anchor_spl::associated_token::get_associated_token_address_with_program_id(
            &owner, &mint, &token,
        )
    {
        return Err(ErrorCode::ConstraintAssociated.into());
    }
    Ok(true)
}

#[derive(Clone)]
pub struct DammProgram;
impl anchor_lang::Id for DammProgram { fn id() -> Pubkey { AMM_PROGRAM } }







use crate::*;












pub fn handle_start_raise(ctx: Context<StartRaise>, funding_duration: u32) -> Result<()> {

    require!(funding_duration <= 604_800, RecoveredError::StartRaise_FundingDurationExceedsMax);
    let mint = ctx.accounts.dao_mint.key();
    let signer_seeds: &[&[&[u8]]] = &[&[b"state", mint.as_ref(), &[ctx.bumps.state]]];
    let cpi_context = ctx.accounts.fundraise_initialize_context().with_signer(signer_seeds);
    let funding_goal = ctx.accounts.state.funding_goal;
    fundraise::cpi::initialize(cpi_context, 850_000_000_000_000_000, funding_goal, funding_duration)?;
    fundraise::cpi::commit_funds(ctx.accounts.fundraise_commit_context(), funding_goal / 10)?;
    Ok(())
}

impl<'info> StartRaise<'info> {
    pub fn fundraise_initialize_context(&self) -> CpiContext<'_, '_, '_, 'info, fundraise::cpi::accounts::Initialize<'info>> {
        let mut authority = self.state.to_account_info();
        authority.is_signer = true;
        let cpi_accounts = fundraise::cpi::accounts::Initialize {
            payer: self.admin.to_account_info(),
            authority,
            token_mint: self.dao_mint.to_account_info(),
            authority_token_vault: self.dao_mint_vault.to_account_info(),
            funding_mint: self.funding_mint.to_account_info(),
            associated_token_program: self.associated_token_program.to_account_info(),
            system_program: self.system_program.to_account_info(),
            token_program: self.token_program.to_account_info(),
            state: self.fundraise_state.to_account_info(),
            token_vault: self.fundraise_token_vault.to_account_info(),
            recipient: self.state.to_account_info(),
            whitelist_authority: self.whitelist_authority.as_ref().map(|w| w.to_account_info()),
        };
        CpiContext::new(self.fundraise_program.to_account_info(), cpi_accounts)
    }
    pub fn fundraise_commit_context(&self) -> CpiContext<'_, '_, '_, 'info, fundraise::cpi::accounts::CommitFunds<'info>> {
        let cpi_accounts = fundraise::cpi::accounts::CommitFunds {
            payer: self.admin.to_account_info(),
            whitelist_authority: self.whitelist_authority.as_ref().map(|w| w.to_account_info()),
            token_mint: self.dao_mint.to_account_info(),
            funding_mint: self.funding_mint.to_account_info(),
            state: self.fundraise_state.to_account_info(),
            payer_token_vault: self.admin_token_vault.to_account_info(),
            payer_funding_vault: self.admin_funding_ata.to_account_info(),
            token_vault: self.fundraise_token_vault.to_account_info(),
            funding_vault: self.fundraise_funding_vault.to_account_info(),
            token_program: self.token_program.to_account_info(),
            funding_token_program: self.funding_token_program.to_account_info(),
            associated_token_program: self.associated_token_program.to_account_info(),
        };
        CpiContext::new(self.fundraise_program.to_account_info(), cpi_accounts)
    }
}

#[derive(Accounts)]
pub struct StartRaise<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    pub dao_mint: Box<InterfaceAccount<'info, Mint>>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(seeds = [b"state", dao_mint.key().as_ref()], bump,
        constraint = state.admin == admin.key() @ RecoveredError::Unauthorized, constraint = state.dao_mint == dao_mint.key() @ RecoveredError::Unauthorized,
        constraint = state.funding_mint == funding_mint.key() @ RecoveredError::Unauthorized, constraint = state.curve_initialized == false @ RecoveredError::StartRaise_InvalidState)]
    pub state: Box<Account<'info, State>>,
    #[account(mut, associated_token::mint = dao_mint, associated_token::authority = state, associated_token::token_program = token_program)]
    pub dao_mint_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: Created by the external fundraise program.
    #[account(mut)]
    pub fundraise_state: UncheckedAccount<'info>,
    /// CHECK: The external program creates and validates this ATA.
    #[account(mut)]
    pub fundraise_token_vault: UncheckedAccount<'info>,
    /// CHECK: Optional authority is passed to the external program.
    pub whitelist_authority: Option<Signer<'info>>,
    #[account(mut, associated_token::mint = dao_mint, associated_token::authority = admin, associated_token::token_program = token_program)]
    pub admin_token_vault: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = admin, associated_token::token_program = funding_token_program)]
    pub admin_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: The external program validates the funding vault.
    #[account(mut)]
    pub fundraise_funding_vault: UncheckedAccount<'info>,
    pub token_program: Program<'info, anchor_spl::token_2022::Token2022>,
    pub funding_token_program: Interface<'info, TokenInterface>,
    pub system_program: Program<'info, System>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    /// CHECK: Program identity and executable flag are constrained.
    
    pub fundraise_program: Program<'info, fundraise::program::Fundraise>,
}




use crate::*;
use anchor_spl::token_2022_extensions::spl_token_metadata_interface::state::TokenMetadata;
use spl_type_length_value::variable_len_pack::VariableLenPack;














pub fn handle_initialize(
    ctx: Context<Initialize>,
    name: String,
    symbol: String,
    uri: String,
    dao_duration_seconds: u32,
    funding_goal: u64,
    carry_basis: Option<u16>,
) -> Result<()> {
    let mint = ctx.accounts.dao_mint.key();

    let seeds: &[&[&[u8]]] = &[&[b"state", mint.as_ref(), &[ctx.bumps.state]]];
    initialize_metadata(&ctx, name.clone(), symbol.clone(), uri.clone(), seeds)?;
    let clock = Clock::get()?;











    let expiration_timestamp = i64::from(dao_duration_seconds) + clock.unix_timestamp;
    let carry_basis = carry_basis.unwrap_or(1000);

    require!(carry_basis <= 4_000, RecoveredError::Init_InvalidCarryBasis);
    ctx.accounts.state.set_inner(State {
        admin: ctx.accounts.admin.key(),
        dao_mint: ctx.accounts.dao_mint.key(),
        funding_mint: ctx.accounts.funding_mint.key(),
        funding_goal,
        admin_closed_fund: false,
        redemption_started: false,
        expiration_timestamp,
        delegate_authorities: [None; 3],
        carry_basis,
        fee_authority: ctx.accounts.fee_authority.key(),
        curve_initialized: false,
    });
    let cpi_program = ctx.accounts.token_program.to_account_info();
    let cpi_accounts = token_interface::MintTo {
        mint: ctx.accounts.dao_mint.to_account_info(),
        to: ctx.accounts.dao_mint_vault.to_account_info(),
        authority: ctx.accounts.state.to_account_info(),
    };
    let cpi_context = CpiContext::new(cpi_program, cpi_accounts).with_signer(seeds);
    token_interface::mint_to(cpi_context, 1_000_000_000_000_000_000)?;
    Ok(())
}









fn initialize_metadata(ctx: &Context<Initialize>, name: String, symbol: String, uri: String, seeds: &[&[&[u8]]]) -> Result<()> {
    let metadata = TokenMetadata {
        name: name.clone(),
        symbol: symbol.clone(),
        uri: uri.clone(),
        ..Default::default()
    };
    let data_len = metadata.get_packed_len()?;








    let data_len = data_len + 4;

    let lamports =
        data_len as u64 * 3480 * 2;
    anchor_lang::system_program::transfer(
        CpiContext::new(ctx.accounts.system_program.to_account_info(), anchor_lang::system_program::Transfer {
            from: ctx.accounts.admin.to_account_info(),
            to: ctx.accounts.dao_mint.to_account_info(),
        }), lamports,
    )?;



    let cpi_program = ctx.accounts.token_program.to_account_info();
    let cpi_accounts = token_interface::TokenMetadataInitialize {
            token_program_id: ctx.accounts.token_program.to_account_info(),
            mint: ctx.accounts.dao_mint.to_account_info(),
            metadata: ctx.accounts.dao_mint.to_account_info(),
            mint_authority: ctx.accounts.state.to_account_info(),
            update_authority: ctx.accounts.state.to_account_info(),
    };
    let cpi_context = CpiContext::new(cpi_program, cpi_accounts).with_signer(seeds);
    token_interface::token_metadata_initialize(cpi_context, name, symbol, uri)?;
    Ok(())
}








#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(init, payer = admin, space = 256, seeds = [b"state", dao_mint.key().as_ref()], bump)]
    pub state: Box<Account<'info, State>>,
    /// Treasury PDA owned by the system program.
    #[account(mut, seeds = [b"wallet", dao_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(init, payer = admin, mint::decimals = 9, mint::authority = state,
        mint::token_program = token_program,
        extensions::metadata_pointer::metadata_address = dao_mint)]
    pub dao_mint: Box<InterfaceAccount<'info, Mint>>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(init, payer = admin, associated_token::mint = dao_mint, associated_token::authority = state,
        associated_token::token_program = token_program)]
    pub dao_mint_vault: InterfaceAccount<'info, TokenAccount>,
    #[account(seeds = [b"fee_share_state", dao_mint.key().as_ref()], bump, seeds::program = fee_share_trader_dao::ID,
        constraint = fee_authority.creator == admin.key() @ RecoveredError::InvalidFeeAuthority,
        constraint = fee_authority.funding_mint == funding_mint.key() @ RecoveredError::InvalidFeeAuthority,
        constraint = fee_authority.dao_mint == dao_mint.key() @ RecoveredError::InvalidFeeAuthority)]
    pub fee_authority: Box<Account<'info, FeeShareState>>,
    pub token_program: Program<'info, anchor_spl::token_2022::Token2022>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
}

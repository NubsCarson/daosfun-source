use anchor_lang::prelude::*;
use anchor_lang::Discriminator;
use solana_program::pubkey;
use anchor_spl::associated_token::AssociatedToken;
use anchor_spl::token_interface::{self, Mint, TokenAccount, TokenInterface, TransferChecked};
mod cosign_instructions; mod errors; use instructions::curve_accounts;
mod instructions;
use instructions::init_curve as curve_handler;
use instructions::migration_accounts;
use instructions::migration_handler;
mod state;     anchor_lang::declare_program!(cp_amm); anchor_lang::declare_program!(dbc);              
pub mod math;
mod pool_math; mod damm_cpi; pub mod dbc_cpi;
pub use state::*;
pub use curve_accounts::*;
pub use migration_accounts::*;
declare_id!("4FqThZWv3QKWkSyXCDmATpWkpEiCHq5yhkdGWpSEDAZM");
pub const CLOSE_AUTHORITY: Pubkey = pubkey!("6ZNfAtWS1C1aPQkrgyPrkWmXuFgnNRTSNYjyxgu5yU7D");
pub const FEE_SHARE_PROGRAM: Pubkey = pubkey!("Fee33nMZNbbC7Zm6Yx7tiHa9KH2Ao8fWTH3HNMkLMzWk");
pub use fundraise::ID as FUNDRAISE_PROGRAM;
pub const AMM_PROGRAM: Pubkey = pubkey!("cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG");
pub const DBC_PROGRAM: Pubkey = pubkey!("dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN");
pub const DBC_CONFIG: Pubkey = pubkey!("BkoMF8PzYwoVQTKcQ6uNeQrHytw1jJN6ig4JzjcKS3iF");

pub use instructions::start_raise::*; pub use cosign_instructions::cosign_init::*; pub use instructions::init::*; pub use instructions::burn_dao_tokens::*; pub use instructions::redeem_sol::*; pub use instructions::redeem_tokens::*; pub use instructions::init_redemption::*;

#[program]
pub mod dao_v1 {
    use super::*;

    pub fn initialize(
        ctx: Context<Initialize>,
        name: String,
        symbol: String,
        uri: String,
        dao_duration_seconds: u32,
        funding_goal: u64,
        carry_basis: Option<u16>,
    ) -> Result<()> {
        instructions::init::handle_initialize(ctx, name, symbol, uri, dao_duration_seconds, funding_goal, carry_basis)
    }

    pub fn add_delegate_authority(ctx: Context<DelegateAuthority>, authority: Pubkey) -> Result<()> { instructions::add_delegate_authority::add_delegate_authority(ctx, authority) }









    pub fn revoke_delegate_authority(ctx: Context<DelegateAuthority>, authority: Pubkey) -> Result<()> { instructions::revoke_delegate_authority::revoke_delegate_authority(ctx, authority) }






















    pub fn execute_invoke<'info>(ctx: Context<'_, '_, '_, 'info, ExecuteInvoke<'info>>, instruction_data: Vec<u8>) -> Result<()> {
        instructions::execute_invoke::handle_execute_invoke(ctx, instruction_data)
    }



































    pub fn start_raise(ctx: Context<StartRaise>, funding_duration: u32) -> Result<()> {
        instructions::start_raise::handle_start_raise(ctx, funding_duration)
    }

























































    pub fn init_curve(ctx: Context<InitCurve>, additional_funding: u64) -> Result<()> {
        curve_handler::initialize(ctx, additional_funding)
    }

    pub fn close_fund(ctx: Context<CloseFund>) -> Result<()> {
        ctx.accounts.state.admin_closed_fund = true;
        Ok(())
    }

    pub fn init_redemption(ctx: Context<InitRedemption>) -> Result<()> {
        instructions::init_redemption::handle_init_redemption(ctx)
    }

    pub fn burn_dao_tokens(ctx: Context<BurnDaoTokens>, dao_mint_amount: u64) -> Result<()> {
        instructions::burn_dao_tokens::handle_burn_dao_tokens(ctx, dao_mint_amount)
    }

    pub fn redeem_sol(ctx: Context<RedeemSol>, amount: u64) -> Result<()> {
        instructions::redeem_sol::handle_redeem_sol(ctx, amount)
    }

    pub fn redeem_tokens(ctx: Context<RedeemTokens>, dao_mint_amount: u64) -> Result<()> {
        instructions::redeem_tokens::handle_redeem_tokens(ctx, dao_mint_amount)
    }

    pub fn cosign_init(ctx: Context<CosignInit>, id: u8, signer: Pubkey) -> Result<()> {
        ctx.accounts.cosign_state.id = id;
        ctx.accounts.cosign_state.signer = signer;
        Ok(())
    }

    pub fn cosign_update_signer(ctx: Context<CosignUpdateSigner>, signer: Pubkey) -> Result<()> {
        ctx.accounts.state.signer = signer;
        Ok(())
    }

    pub fn migrate_bonding_to_meteora(ctx: Context<MigrateBondingToMeteora>) -> Result<()> {
        migration_handler::migrate(ctx)
    }

    pub fn init_bonding_on_meteora(
        ctx: Context<InitBondingOnMeteora>,
        name: String,
        symbol: String,
        uri: String,
    ) -> Result<()> {
        bonding_handlers::initialize(ctx, name, symbol, uri)
    }















































    pub fn finalize_meteora_bonding(ctx: Context<FinalizeMeteoraBonding>) -> Result<()> {
        bonding_handlers::finalize(ctx)
    }























    pub fn transfer_position_nft_to_fee_share(
        ctx: Context<TransferPositionNftToFeeShare>,
    ) -> Result<()> {
        let seeds: &[&[&[u8]]] = &[&[b"meteora_authority", &[ctx.bumps.meteora_authority]]];
        anchor_spl::token_interface::set_authority(
            ctx.accounts.transfer_nft_context().with_signer(seeds),
            anchor_spl::token_2022::spl_token_2022::instruction::AuthorityType::AccountOwner,
            Some(ctx.accounts.fee_authority.key()),
        )?;
        Ok(())
    }









    pub fn claim_dbc_trading_fees(ctx: Context<ClaimDbcTradingFees>) -> Result<()> {
        bonding_handlers::claim(ctx)
    }

































































}

#[repr(C)]
#[derive(Clone, Copy, AnchorSerialize, AnchorDeserialize, bytemuck::Pod, bytemuck::Zeroable)]
pub struct ExternalDbcConfig {
    pub prefix: [u64; 32],
    pub migration_quote_threshold: u64,
    pub remainder: [u64; 97],
}
impl anchor_lang::ZeroCopy for ExternalDbcConfig {}
impl Owner for ExternalDbcConfig {
    fn owner() -> Pubkey {
        DBC_PROGRAM
    }
}
impl Discriminator for ExternalDbcConfig {
    const DISCRIMINATOR: [u8; 8] = [26, 108, 14, 123, 116, 230, 129, 43];
}































































































































/// Only identity fields are interpreted. The remaining deployed zero-copy bytes
/// are retained as opaque words, not claimed as recovered financial fields.
#[repr(C)]
#[derive(Clone, Copy, AnchorSerialize, AnchorDeserialize, bytemuck::Pod, bytemuck::Zeroable)]
pub struct ExternalPool {
    pub fee_data: [u64; 20],
    pub token_a_mint: Pubkey,
    pub token_b_mint: Pubkey,
    pub remaining: [u64; 110],
}
impl anchor_lang::ZeroCopy for ExternalPool {}
impl Owner for ExternalPool {
    fn owner() -> Pubkey {
        AMM_PROGRAM
    }
}
impl Discriminator for ExternalPool {
    const DISCRIMINATOR: [u8; 8] = [241, 154, 109, 4, 17, 177, 109, 188];
}
pub use cp_amm::accounts::Position as ExternalPosition;






























fn external_invoke<'info>(
    program: AccountInfo<'info>,
    accounts: Vec<(AccountInfo<'info>, bool, bool)>,
    data: Vec<u8>,
    seeds: &[&[&[u8]]],
) -> Result<()> {
    use anchor_lang::solana_program::{
        instruction::{AccountMeta, Instruction},
        program::invoke_signed,
    };
    let metas = accounts
        .iter()
        .map(|(a, signer, writable)| AccountMeta {
            pubkey: a.key(),
            is_signer: *signer,
            is_writable: *writable,
        })
        .collect();
    let mut infos: Vec<_> = accounts.into_iter().map(|(a, _, _)| a).collect();
    let program_id = program.key();
    infos.push(program);
    invoke_signed(
        &Instruction {
            program_id,
            accounts: metas,
            data,
        },
        &infos,
        seeds,
    )
    .map_err(Into::into)
}







































/// External account layout inferred from serialization probes. Counter field names
/// are provisional; this program only reads the three identity fields.






































































// All 24 variant names recovered by bounded interpretation of the original error-name routine.




















































#[derive(Clone)]
pub struct DbcProgram;
impl anchor_lang::Id for DbcProgram { fn id() -> Pubkey { DBC_PROGRAM } }



pub mod bonding_handlers;

pub use instructions::bonding::init_bonding_on_meteora::*;



pub use instructions::init_curve::check_curve_pda;

pub use instructions::{add_delegate_authority, revoke_delegate_authority};

pub use errors::RecoveredError;
pub use cosign_instructions::cosign_update_signer::*;

pub use instructions::add_delegate_authority::*;

pub use instructions::execute_invoke::*;

pub use instructions::close_fund::*;

pub use instructions::bonding::finalize_meteora_bonding::*;

pub use instructions::bonding::transfer_position_nft_to_fee_share::*;

pub use instructions::bonding::claim_dbc_trading_fees::*;

//! Compatibility wrappers while recovering the original module layout.
use crate::math::migration_math;
pub const MIN_SQRT_PRICE: u128 = 4_295_048_016;
pub const MAX_SQRT_PRICE: u128 = 79_226_673_521_066_979_257_578_248_091;

pub fn initial_sqrt_price(amount_a: u128, amount_b: u128) -> u128 {
    migration_math::get_initial_sqrt_price(amount_a, amount_b, MIN_SQRT_PRICE, MAX_SQRT_PRICE)
}

pub fn initial_liquidity(amount_a: u128, amount_b: u128, price: u128) -> u128 {
    migration_math::liquidity_from_a(amount_a, price, MAX_SQRT_PRICE)
        .min(migration_math::liquidity_from_b(amount_b, MIN_SQRT_PRICE, price))
}

#[path = "../src/pool_math.rs"]
mod pool_math;
fn main() {
    let s = pool_math::initial_sqrt_price(150_000_000_000_000_000, 800_000_000);
    println!(
        "sqrt={s} liquidity={}",
        pool_math::initial_liquidity(150_000_000_000_000_000, 800_000_000, s)
    );
}

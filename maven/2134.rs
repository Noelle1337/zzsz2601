// cart.rs —— 所有权 + Result + 迭代器
#[derive(Debug, Clone)]
struct Item {
    name: String,
    price: f64,
    qty: u32,
}

#[derive(Default)]
struct Cart {
    items: Vec<Item>,
}

impl Cart {
    fn new() -> Self {
        Cart::default()
    }

    fn add(&mut self, name: &str, price: f64, qty: u32) -> Result<(), String> {
        if price < 0.0 || qty == 0 {
            return Err("价格或数量不合法".to_string());
        }
        match self.items.iter_mut().find(|i| i.name == name) {
            Some(item) => item.qty += qty,
            None => self.items.push(Item {
                name: name.to_string(),
                price,
                qty,
            }),
        }
        Ok(())
    }

    fn remove(&mut self, name: &str) {
        self.items.retain(|i| i.name != name);
    }

    fn total(&self) -> f64 {
        self.items.iter().map(|i| i.price * i.qty as f64).sum()
    }

    fn receipt(&self) -> String {
        let mut out: String = self
            .items
            .iter()
            .map(|i| format!("{} x{}  ¥{:.2}\n", i.name, i.qty, i.price * i.qty as f64))
            .collect();
        out.push_str(&"-".repeat(26));
        out.push_str(&format!("\n合计: ¥{:.2}", self.total()));
        out
    }
}

fn main() -> Result<(), String> {
    let mut cart = Cart::new();
    cart.add("机械键盘", 399.0, 1)?;
    cart.add("鼠标垫", 29.9, 2)?;
    cart.add("机械键盘", 399.0, 1)?;

    println!("{}", cart.receipt());

    cart.remove("鼠标垫");
    println!("移除后总价: ¥{:.2}", cart.total());
    Ok(())
}
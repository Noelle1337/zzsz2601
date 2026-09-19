// cart.ts —— 类型系统 + 泛型 + 异步
interface Item {
  readonly name: string;
  readonly price: number;
  qty: number;
}

type PayFn = (amount: number) => Promise<string>;

class ShoppingCart {
  private items: Item[] = [];

  add(name: string, price: number, qty = 1): this {
    if (price < 0 || qty <= 0) throw new Error("价格或数量不合法");
    const existing = this.items.find(i => i.name === name);
    if (existing) existing.qty += qty;
    else this.items.push({ name, price, qty });
    return this;
  }

  remove(name: string): this {
    this.items = this.items.filter(i => i.name !== name);
    return this;
  }

  get total(): number {
    return this.items.reduce((sum, i) => sum + i.price * i.qty, 0);
  }

  get receipt(): string {
    const lines = this.items.map(
      i => `${i.name} x${i.qty}  ¥${(i.price * i.qty).toFixed(2)}`
    );
    lines.push("─".repeat(26), `合计: ¥${this.total.toFixed(2)}`);
    return lines.join("\n");
  }

  async checkout<T extends PayFn>(pay: T): Promise<string> {
    if (this.items.length === 0) throw new Error("购物车是空的");
    const result = await pay(this.total);
    this.items = [];
    return result;
  }
}

// 使用示例
const cart = new ShoppingCart()
  .add("机械键盘", 399)
  .add("鼠标垫", 29.9, 2)
  .add("机械键盘", 399);

console.log(cart.receipt);

const pay: PayFn = amount =>
  new Promise(resolve => setTimeout(() => resolve(`支付成功: ¥${amount.toFixed(2)}`), 500));

cart.checkout(pay).then(console.log);
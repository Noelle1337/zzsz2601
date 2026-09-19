class ShoppingCart {
  #items = [];

  // 添加商品,若已存在则累加数量
  add(name, price, qty = 1) {
    if (price < 0 || qty <= 0) throw new Error('价格或数量不合法');
    const existing = this.#items.find(item => item.name === name);
    if (existing) {
      existing.qty += qty;
    } else {
      this.#items.push({ name, price, qty });
    }
    return this; // 支持链式调用
  }

  // 移除商品
  remove(name) {
    this.#items = this.#items.filter(item => item.name !== name);
    return this;
  }

  // 总价(getter)
  get total() {
    return this.#items.reduce((sum, { price, qty }) => sum + price * qty, 0);
  }

  // 生成小票文本
  get receipt() {
    const lines = this.#items.map(
      ({ name, price, qty }) => `${name} x${qty}  ¥${(price * qty).toFixed(2)}`
    );
    lines.push('—'.repeat(24));
    lines.push(`合计:¥${this.total.toFixed(2)}`);
    return lines.join('\n');
  }

  // 异步结算
  async checkout(payFn) {
    if (this.#items.length === 0) throw new Error('购物车是空的');
    const result = await payFn(this.total);
    this.#items = [];
    return result;
  }
}
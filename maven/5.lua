-- cart.lua —— table + 元表 + 闭包风格
local Cart = {}
Cart.__index = Cart

function Cart.new()
    return setmetatable({ items = {} }, Cart)
end

function Cart:add(name, price, qty)
    qty = qty or 1
    assert(price >= 0 and qty > 0, "价格或数量不合法")
    for _, it in ipairs(self.items) do
        if it.name == name then
            it.qty = it.qty + qty
            return self
        end
    end
    table.insert(self.items, { name = name, price = price, qty = qty })
    return self
end

function Cart:remove(name)
    for i = #self.items, 1, -1 do
        if self.items[i].name == name then
            table.remove(self.items, i)
        end
    end
    return self
end

function Cart:total()
    local sum = 0
    for _, it in ipairs(self.items) do
        sum = sum + it.price * it.qty
    end
    return sum
end

function Cart:receipt()
    local lines = {}
    for _, it in ipairs(self.items) do
        lines[#lines + 1] = string.format("%s x%d  ¥%.2f", it.name, it.qty, it.price * it.qty)
    end
    lines[#lines + 1] = string.rep("-", 26)
    lines[#lines + 1] = string.format("合计: ¥%.2f", self:total())
    return table.concat(lines, "\n")
end

-- 使用示例
local cart = Cart.new():add("机械键盘", 399):add("鼠标垫", 29.9, 2):add("机械键盘", 399)
print(cart:receipt())
cart:remove("鼠标垫")
print(("移除后总价: ¥%.2f"):format(cart:total()))
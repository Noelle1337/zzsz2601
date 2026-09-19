// Cart.java —— record + Stream + Optional
import java.util.*;
import java.util.stream.*;

record Item(String name, double price, int qty) {
    Item {
        if (price < 0 || qty <= 0) {
            throw new IllegalArgumentException("价格或数量不合法");
        }
    }

    double subtotal() {
        return price * qty;
    }
}

public class Cart {
    private final List<Item> items = new ArrayList<>();

    public Cart add(String name, double price, int qty) {
        Optional<Item> hit = items.stream()
                .filter(i -> i.name().equals(name))
                .findFirst();

        if (hit.isPresent()) {
            Item old = hit.get();
            items.set(items.indexOf(old), new Item(name, price, old.qty() + qty));
        } else {
            items.add(new Item(name, price, qty));
        }
        return this;
    }

    public Cart remove(String name) {
        items.removeIf(i -> i.name().equals(name));
        return this;
    }

    public double total() {
        return items.stream().mapToDouble(Item::subtotal).sum();
    }

    public String receipt() {
        String body = items.stream()
                .map(i -> String.format("%s x%d  ¥%.2f", i.name(), i.qty(), i.subtotal()))
                .collect(Collectors.joining("\n"));

        return body + "\n" + "-".repeat(26)
                + String.format("%n合计: ¥%.2f", total());
    }

    public static void main(String[] args) {
        Cart cart = new Cart()
                .add("机械键盘", 399, 1)
                .add("鼠标垫", 29.9, 2)
                .add("机械键盘", 399, 1);

        System.out.println(cart.receipt());

        cart.remove("鼠标垫");
        System.out.printf("移除后总价: ¥%.2f%n", cart.total());
    }
}
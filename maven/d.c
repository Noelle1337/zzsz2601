/* cart.c —— struct + 数组 + 手动内存管理 */
#include <stdio.h>
#include <string.h>

#define MAX_ITEMS  16
#define NAME_LEN   32

typedef struct {
    char   name[NAME_LEN];
    double price;
    int    qty;
} Item;

typedef struct {
    Item items[MAX_ITEMS];
    int  count;
} Cart;

static void cart_init(Cart *c)
{
    c->count = 0;
}

/* 返回 0 成功,-1 失败 */
static int cart_add(Cart *c, const char *name, double price, int qty)
{
    int i;

    if (price < 0 || qty <= 0 || c->count >= MAX_ITEMS)
        return -1;

    for (i = 0; i < c->count; ++i) {
        if (strcmp(c->items[i].name, name) == 0) {
            c->items[i].qty += qty;
            return 0;
        }
    }

    snprintf(c->items[c->count].name, NAME_LEN, "%s", name);
    c->items[c->count].price = price;
    c->items[c->count].qty   = qty;
    c->count++;
    return 0;
}

static void cart_remove(Cart *c, const char *name)
{
    int i, j;

    for (i = 0; i < c->count; ++i) {
        if (strcmp(c->items[i].name, name) == 0) {
            for (j = i; j < c->count - 1; ++j)
                c->items[j] = c->items[j + 1];
            c->count--;
            return;
        }
    }
}

static double cart_total(const Cart *c)
{
    double sum = 0;
    int i;

    for (i = 0; i < c->count; ++i)
        sum += c->items[i].price * c->items[i].qty;
    return sum;
}

static void cart_receipt(const Cart *c)
{
    int i;

    for (i = 0; i < c->count; ++i) {
        const Item *it = &c->items[i];
        printf("%s x%d  ¥%.2f\n", it->name, it->qty, it->price * it->qty);
    }
    puts("--------------------------");
    printf("合计: ¥%.2f\n", cart_total(c));
}

int main(void)
{
    Cart cart;
    cart_init(&cart);

    cart_add(&cart, "机械键盘", 399.0, 1);
    cart_add(&cart, "鼠标垫",   29.9,  2);
    cart_add(&cart, "机械键盘", 399.0, 1);

    cart_receipt(&cart);

    cart_remove(&cart, "鼠标垫");
    printf("移除后总价: ¥%.2f\n", cart_total(&cart));

    return 0;
}
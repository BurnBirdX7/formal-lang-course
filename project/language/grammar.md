## Грамматика

### Описание абстрактного синтаксиса языка

```
prog = List<stmt>

stmt =
    bind of var * expr
  | print of expr

intSet =
    Set of int
  | Set of Set<int>

val =
    String of string
  | Int of int
  | IntRange of int * int
  | IntSet of intSet

expr =
    Var of var                   // переменные
  | Val of val                   // константы
  | Set_start of Set<val> * expr // задать множество стартовых состояний
  | Set_final of Set<val> * expr // задать множество финальных состояний
  | Add_start of Set<val> * expr // добавить состояния в множество стартовых
  | Add_final of Set<val> * expr // добавить состояния в множество финальных
  | Get_start of expr            // получить множество стартовых состояний
  | Get_final of expr            // получить множество финальных состояний
  | Get_reachable of expr        // получить все пары достижимых вершин
  | Get_vertices of expr         // получить все вершины
  | Get_edges of expr            // получить все рёбра
  | Get_labels of expr           // получить все метки
  | Map of lambda * expr         // классический map
  | Filter of lambda * expr      // классический filter
  | Load of path                 // загрузка графа
  | Intersect of expr * expr     // пересечение языков
  | Concat of expr * expr        // конкатенация языков
  | Union of expr * expr         // объединение языков
  | Star of expr                 // замыкание языков (звезда Клини)
  | Smb of expr                  // единичный переход

lambda =
    Lamda of Set<var> * expr
```


### Конкретный синтаксис

[ANTLR4](Language.g4)

### Пример запроса

```
// Загрузить граф "wine"
let g' = load "wine";

// Установим все вершины графа финальными и вершины с 0 по 100 - стартовыми
let g = set starts of (set finals of g' as (get_vertices of g')) as {0..100};

// Язык из строк "l1" и "l2"
let l1 = "l1" | "l2";

// Объединение языков "type" и l1 и замыкание результирующего языка
let q1 = ("type" | l1)*;

// Конкатенация языков
let q2 = "sub_class_of" ++ l1;

// Пересечение языков
let res1 = g & q1;
let res2 = g & q2;

// Напечатать язык res1
print res1;

// Получим стартовые вергины языка
let s = get_starts of g;

// Фильтры и мапы, берём все рёбра языка, выбираем вершины из которых ребро выходит,
// отфильтровываем те вершины которые не входят в число начальных вершин `g`
let vertices1 = filter (map (get_edges of res1) with \[[u_g,u_q1],l,[v_g,v_q1]] -> u_g) with \v -> (v in s);
let vertices2 = filter (map (get_edges of res2) with \[[u_g,u_q2],l,[v_g,v_q2]] -> u_g) with \v -> (v in s);

// Объединим полученные наборы вершин
let vertices = vertices1 | vertices2;

// Напечатаем
print vertices;
```

[Дерево для примера](exampleTree.png) \
[Дерево построенное с помощью DOTBuilder](myExampleTree.png)

grammar Language;

program: (stmt ';')* EOF;

stmt:
      bind
    | print;

bind: 'let' pattern '=' expr;
print: 'print' expr;
comment: COMMENT;

pattern: var | '[' pattern (',' pattern)* ']';

var: VAR;
val: STRING | INT | intSet;

intSet:
      '{' '}'                   // empty set
    | ('{' INT (',' INT)* '}')  // set of listed elements
    | '{' INT '..' INT '}';     // set of integers in a certain range

lambda:
    ('\\' | 'λ') pattern '->' expr;

expr:
      var                                 // переменные
    | val                                 // константы
    | 'set' 'starts' 'of' expr 'as' expr  // задать множество стартовых состояний
    | 'set' 'finals' 'of' expr 'as' expr  // задать множество финальных состояний
    | 'add' expr 'as' 'starts' 'of' expr // добавить состояния в множество стартовых
    | 'add' expr 'as' 'finals' 'of' expr // добавить состояния в множество финальных
    | 'get_starts' 'of' expr           // получить множество стартовых состояний
    | 'get_finals' 'of' expr           // получить множество финальных состояний
    | 'get_reachable' 'of' expr        // получить все пары достижимых вершин
    | 'get_vertices' 'of' expr         // получить все вершины
    | 'get_edges' 'of' expr            // получить все рёбра
    | 'get_labels' 'of' expr           // получить все метки
    | 'map' expr 'with' lambda           // классический map
    | 'filter' expr 'with' lambda        // классический filter
    | 'load' (var | STRING)              // загрузка графа
    | expr '&' expr                      // пересечение языков
    | expr '++' expr                     // конкатенация языков
    | expr '|' expr                      // объединение языков
    | expr '*'                           // замыкание языков (звезда Клини)
    | 'tans' expr                        // единичный переход
    | expr 'in' expr
    | '(' expr ')';

VAR: [a-zA-Z_][a-zA-Z0-9_']*;
STRING: '"' ~["]* '"'; // to allow string to contain escaped characters
INT: [0-9]+;
COMMENT: '//' (~('\n'|'\r'))* -> skip; // Consume everything that is not an end of line
WS: [ \t\r\n\u000C] -> skip;

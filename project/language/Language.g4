grammar Language;

program: (stmt ';')* EOF;

stmt:
      bind
    | print;

bind: 'let' pattern '=' expr;
print: 'print' expr;

comment: COMMENT;

pattern:
      VAR                            # patternVar
    | '[' pattern (',' pattern)* ']' # patternPattern
    ;

val: STRING | INT | intSet | tuple;

intSet:
      '{' '}'                  # setEmpty   // empty set
    | ('{' INT (',' INT)* '}') # setList    // set of listed elements
    | '{' INT '..' INT '}'     # setRange   // set of integers in a certain range
    ;

tuple: '[' val (',' val)* ']';

lambda:
    ('\\' | 'λ') pattern '->' expr;

expr:
      VAR                                # exprVar          // переменные
    | val                                # exprVal          // константы
    | 'set' 'starts' 'of' expr 'as' expr # exprSetStarts    // задать множество стартовых состояний
    | 'set' 'finals' 'of' expr 'as' expr # exprSetFinals    // задать множество финальных состояний

    | 'add' expr 'as' 'starts' 'of' expr # exprAddStarts    // добавить состояния в множество стартовых
    | 'add' expr 'as' 'finals' 'of' expr # exprAddFinals    // добавить состояния в множество финальных
    | 'get_starts' 'of' expr             # exprGetStarts    // получить множество стартовых состояний
    | 'get_finals' 'of' expr             # exprGetFinals    // получить множество финальных состояний
    | 'get_reachable' 'of' expr          # exprGetReachable // получить все пары достижимых вершин
    | 'get_vertices' 'of' expr           # exprGetVertices  // получить все вершины
    | 'get_edges' 'of' expr              # exprGetEdges     // получить все рёбра
    | 'get_labels' 'of' expr             # exprGetLabels    // получить все метки
    | 'map' expr 'with' lambda           # exprMap          // классический map
    | 'filter' expr 'with' lambda        # exprFilter       // классический filter
    | 'load' (VAR | val)                 # exprLoad         // загрузка графа
    | expr '&' expr                      # exprProduct      // пересечение языков
    | expr '++' expr                     # exprConcat       // конкатенация языков
    | expr '|' expr                      # exprUnion        // объединение языков
    | expr '*'                           # exprKleene       // замыкание языков (звезда Клини)
    | 'trans' expr                       # exprTransition   // единичный переход
    | expr 'in' expr                     # exprIn
    | '(' expr ')'                       # exprBraced
    ;

VAR: [a-zA-Z_][a-zA-Z0-9_']*;
STRING: '"' ~["]* '"'; // to allow string to contain escaped characters
INT: '-'?[0-9]+;
COMMENT: '//' (~('\n'|'\r'))* -> skip; // Consume everything that is not an end of line
WS: [ \t\r\n\u000C] -> skip;

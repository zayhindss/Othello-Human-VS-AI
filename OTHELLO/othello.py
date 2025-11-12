#==============BOARD SETUP====================
EMPTY, BLACK, WHITE, OUTER = '.', '@', 'o', '?'
PLAYERS = {BLACK: 'Black', WHITE: 'White'}

#==========DIRECTION STEPS=================
UP, DOWN, LEFT, RIGHT = -10, 10, -1, 1
UP_RIGHT, DOWN_RIGHT, DOWN_LEFT, UP_LEFT = -9, 11, 9, -11
DIRECTIONS = (UP, UP_RIGHT, RIGHT, DOWN_RIGHT, DOWN, DOWN_LEFT, LEFT, UP_LEFT)

#==============CORE BOARD HELPERS==============================
def squares():
    #return the 64 playable indices (11-88) skipping outer ring
    return [i for i in range(11, 89) if 1 <= (i % 10) <= 8]

def initial_board():
    #builds a 10x10 board with outer board sentinels and 4 center discs
    #middle 4 squares are initialized in standard othello-y way
    board = [OUTER] * 100
    for i in squares():
        board[i] = EMPTY
    board[44], board[45] = WHITE, BLACK
    board[54], board[55] = BLACK, WHITE
    return board

def print_board(board):
    #builds a ASCII rep of the board with 1-8 row/column labels
    lines = []
    lines.append("   " + " ".join(str(c) for c in range(1, 9)))
    for row in range(1, 9):
        begin, end = 10*row + 1, 10*row + 9
        lines.append(f"{row}  " + " ".join(board[begin:end]))
    return "\n".join(lines)

def opponent(player):
    #return opp disc color
    return BLACK if player == WHITE else WHITE

def is_valid(move):
    #check that an index is one of the 64 playable squares
    return move in squares()

#==================MOVE LEGALITY=========================
def find_bracket(square, player, board, direction):
    #checks one direction to find a valid bracket
    #start from move and walk along until hitting same color or empty
    bracket = square + direction
    if board[bracket] != opponent(player):
        return None
    while board[bracket] == opponent(player):
        bracket += direction
    return bracket if board[bracket] == player else None

def is_legal(move, player, board):
    # a move is legal iff: 
    #1) it targets a valid EMPTY square
    #2) in at least one of the 8 directions we can find a bracket via find_bracket()
    if not is_valid(move) or board[move] != EMPTY:
        return False
    for d in DIRECTIONS:
        if find_bracket(move, player, board, d) is not None:
            return True
    return False

def legal_moves(player, board):
    #list all legal move positions for gievn player
    return [sq for sq in squares() if is_legal(sq, player, board)]

def any_legal_move(player, board):
    #quickly check if given player has any legal moves
    for sq in squares():
        if is_legal(sq, player, board):
            return True
    return False

def make_move(move, player, board):
    #executes the move and flips all bracketed opponent pieces
    #returns a new board that does NOT mutate original, so its a copy of new board.
    new_board = list(board)
    if move is None:
        return new_board
    new_board[move] = player
    for d in DIRECTIONS:
        bracket = find_bracket(move, player, new_board, d)
        if bracket is not None:
            sq = move + d
            while sq != bracket:
                new_board[sq] = player
                sq += d
    return new_board

#=====================TURN LOGIC / SCORING =======================
def next_player(prev_player, board):
    #choose who moves next
    #if opp has legal move, its their turn
    #else, if prev_player has a legal move, they play again (opp passes)
    #if neither has a legal move, game is over
    opp = opponent(prev_player)
    if any_legal_move(opp, board):
        return opp
    if any_legal_move(prev_player, board):
        return prev_player
    return None

def score(player, board):
    #return a signed disc diff from player's perspective. useful for quick evals and printing final result
    opp = opponent(player)
    p = 0
    for s in board:
        if s == player:
            p += 1
        elif s == opp:
            p -= 1
    return p

#=====================HUMAN STUFF===========================
def human_strategy(player, board):
    #lets human pick moves
    #shows board and legal move list
    #handles quitting, and if a user passes
    print("\n" + print_board(board))
    moves = legal_moves(player, board)
    if not moves:
        print(f"{PLAYERS[player]} has no legal moves and must pass.")
        return None
    print(f"{PLAYERS[player]}'s legal moves: {sorted(moves)}")
    while True:
        raw = input(f"Enter move for {PLAYERS[player]} (e.g., 34) or 'q' to quit: ").strip()
        if raw.lower() in ('q', 'quit', 'exit'):
            print("Exiting game.")
            raise SystemExit
        try:
            mv = int(raw)
        except ValueError:
            print("Please enter an integer like 34 (rowcol).")
            continue
        if mv in moves:
            return mv
        print("Illegal move. Try again.")

#====================PLAY=====================
#game loop
def play(black_strategy, white_strategy):
    board = initial_board()
    player = BLACK
    #sets colors to each player : strat = { '@': human_strategy, 'o': ai_strategy }
    strat = {BLACK: black_strategy, WHITE: white_strategy}
    print("\nStarting position:\n" + print_board(board))

    while player is not None:
        #if player == BLACK, strat[player] is human_strategy, so this calls human_strategy
        #if player == WHITE, strat[player] is ai_strategy, so this calls ai_strategy
        move = strat[player](player, board)
        #applies move and flips necessary pieces
        board = make_move(move, player, board)
        #decides who moves next (also handles passes or game ending)
        player = next_player(player, board)

    print("\nFinal position:\n" + print_board(board))
    b = sum(1 for s in board if s == BLACK)
    w = sum(1 for s in board if s == WHITE)
    print(f"Score -> Black(@): {b}  White(o): {w}")

    if b > w:
        print("Black wins!")
    elif w > b:
        print("White wins!")
    else:
        print("Draw!")

#======================AI STUFF=====================
AI_SEARCH_DEPTH = 4 
#counts how many nodes minimax visited for the CURRENT AI move
NODES_EXAMINED = 0

#IMPORTANT BOARD POSITIONS
CORNERS = (11, 18, 81, 88) #very advantageous spots
X_SQUARES = (22, 27, 72, 77) #spots diagonal to corners (dangerous early game)
C_SQUARES = (12, 17, 21, 28, 71, 78, 82, 87) #side adjacent (near corner/sketchy early game because it sets up opp to grab corner after)

#checks if game is over : if black nor white has NO legal moves left, tells AI to stop searching ahead
def terminal(board):
    return (not any_legal_move(BLACK, board)) and (not any_legal_move(WHITE, board))

#how AI scores a board position to decide if its good or bad
def evaluate(board, root_player):
    #finds out who opp is
    opp = opponent(root_player)

    #corner control
    corner_score = 0
    for c in CORNERS:
        #if AI owns corner, +1
        if board[c] == root_player:
            corner_score += 1
        #if opp (player) owns corner, -1
        elif board[c] == opp:
            corner_score -= 1

    #mobility (how many options each side has)
    #if you have more freedom of movement, you have an advantage
    #if you're boxed in, you're losing control
    mob = len(legal_moves(root_player, board)) - len(legal_moves(opp, board))

    #disc difference
    #measures how much of the board the AI owns over player
    discdiff = score(root_player, board)

    #danger (near-corner occupancy (penalize))
    #if AI is sitting too close to a corner (before it owns it) it can be "punished"
    #the reason why is because opp (player) can take that corner next turn
    x_diff = sum(1 for x in X_SQUARES if board[x] == root_player) - sum(1 for x in X_SQUARES if board[x] == opp)
    c_diff = sum(1 for c in C_SQUARES if board[c] == root_player) - sum(1 for c in C_SQUARES if board[c] == opp)

    #final weighted score
    #25x corner_score : very important
    #+5x mobility : kinda important
    #+1x disc diff : slightly important
    #-4x x_diff and -2x c_diff : avoids danger near corners
    #basically this formula is the AI's way of deciding how beneficial the board is to it
    return 25 * corner_score + 5 * mob + 1 * discdiff - 4 * x_diff - 2 * c_diff

def minimax(board, player_to_move, depth, root_player):
    global NODES_EXAMINED
    NODES_EXAMINED += 1
    #step 1 : base case
    #if ai has looked ahead enough (depth == 0), or the game is over (terminal board), it returns a score with evaluate
    if depth == 0 or terminal(board):
        return evaluate(board, root_player), None

    #step 2 : get all legal moves
    #finds out what moves current player can make right now
    moves = legal_moves(player_to_move, board)

    #if no legal move: forced pass
    if not moves:
        child = make_move(None, player_to_move, board)
        nxt = next_player(player_to_move, child)
        if nxt is None:
            return evaluate(child, root_player), None
        val, _ = minimax(child, nxt, depth - 1, root_player)
        return val, None

    #order moves with a tiny preference: corners first (a tiny heuristic)
    def move_key(m):
        return 0 if m in CORNERS else 1
    moves = sorted(moves, key=move_key)

    #decides whether to maximize or minimize at this node
    #if ai's turn, maximize (to get highest score)
    #if opp's turn, minimize (to get lowest score, because opp wants to win)
    maximizing = (player_to_move == root_player)
    #initializes best_val to very low if max, very high if min
    best_val = -10**9 if maximizing else 10**9
    #initializes best_move to first legal move (sade because no moves case was already handled)
    best_move = moves[0]

    #simulates each move
    #plays a move imagining what the opp (player) would do and repeats until it hits maximum depth
    #everytime it gets a "value", whihc determines how good or bad the end board was
    for mv in moves:
        child = make_move(mv, player_to_move, board) #builds child board (does the flips)
        nxt = next_player(player_to_move, child) #tells us who moves next
        if nxt is None:
            val = evaluate(child, root_player)
            #move ends game, evaluate immediately
        else:
            val, _ = minimax(child, nxt, depth - 1, root_player)
            #recurse one ply deeper with a reduced depth, but in nxt's turn
            #the result of this is val : the "goodness" of this move's future from the root player's perspective

        if maximizing:
            #keeps highest score, if this move's val is larger than the best so far, update the record
            #or is the tiebreaker : if two moves have == score, pick the one wihth smaller move index (mv) to keep results from randomness
            if val > best_val or (val == best_val and mv < best_move):
                best_val, best_move = val, mv
        else:
            #keeps lowest score, because when its opp's turn, they want to make AI's situation as bad as possible
            #same tie-breaker
            if val < best_val or (val == best_val and mv < best_move):
                best_val, best_move = val, mv

    #after checking every legal move, it returns 
    #best_val : score for BEST line of play assuming perfect play by both sides
    #best_move : the ACTUAL move to take now that leads to that best line
    return best_val, best_move

def ai_strategy(player, board):
    global AI_SEARCH_DEPTH, NODES_EXAMINED

    print("\n" + print_board(board))

    mv_count = len(legal_moves(player, board))
    if mv_count == 0:
        print(f"{PLAYERS[player]} (AI) has no legal moves and must pass.")
        return None

    #let user optionally change depth for this move, and changes stay
    prompt = (
        f"[AI] Current search depth: {AI_SEARCH_DEPTH}. "
        "Press Enter to keep, or type a new integer depth: "
    )
    raw = input(prompt).strip()
    if raw:
        try:
            d = int(raw)
            if d >= 1:
                AI_SEARCH_DEPTH = d  #new depth stays
            else:
                print("Depth must be >= 1; keeping previous depth.")
        except ValueError:
            print("Not an integer; keeping previous depth.")

    #reset node counter and run search
    NODES_EXAMINED = 0
    val, choice = minimax(board, player, AI_SEARCH_DEPTH, player)
    print(f"{PLAYERS[player]} (AI) chooses move {choice} "f"[depth={AI_SEARCH_DEPTH}, eval={val}, states_examined={NODES_EXAMINED}]")
    return choice

# ===================END AI STUFF===================

#=================MAIN MENU=========================
def ai_color():
    print("\n=====Human vs AI setup=====")
    print("Who should play BLACK (@)?  (Black moves first.)")
    print("1) Human plays BLACK (@), Computer plays WHITE (o)")
    print("2) Computer plays BLACK (@), Human plays WHITE (o)")
    choice = ""
    while choice not in ("1", "2"):
        choice = input("Choose 1 or 2: ").strip()
    return choice

def main():
    print("\n====== OTHELLO ======")
    print("1) Two humans play")
    print("2) Human vs AI")
    print("=====================\n")

    choice = ""
    while choice not in ("1", "2"):
        choice = input("Choose a mode (1 or 2): ").strip()

    if choice == "1":
        print("\nMode: Two humans")
        play(human_strategy, human_strategy)
    else:
        pick = ai_color()
        if pick == "1":
            #human is black, AI is white
            print("\nMode: HUMAN (BLACK @) vs AI (WHITE o)")
            play(human_strategy, ai_strategy)
        else:
            #AI is black, human is white
            print("\nMode: AI (BLACK @) vs HUMAN (WHITE o)")
            play(ai_strategy, human_strategy)

if __name__ == "__main__":
    main()



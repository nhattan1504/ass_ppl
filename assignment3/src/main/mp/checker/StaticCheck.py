
"""
 * @author nhphung
"""
from AST import *
from Visitor import *
from Utils import Utils
from StaticError import *
from functools import reduce


class MType:
    def __init__(self, partype, rettype):
        self.partype = partype
        self.rettype = rettype


class Symbol:
    def __init__(self, name, mtype, value=None):
        self.name = name
        self.mtype = mtype
        self.value = value


class StaticChecker(BaseVisitor, Utils):

    global_envi = [Symbol("getInt", MType([], IntType())),
                   Symbol("putInt", MType([IntType()], VoidType())),
                   Symbol("putIntLn", MType([IntType()], VoidType())),
                   Symbol("getFloat", MType([], FloatType())),
                   Symbol("putFloat", MType([FloatType()], VoidType())),
                   Symbol("putFloatLn", MType([FloatType()], VoidType())),
                   Symbol("putBool", MType([BoolType()], VoidType())),
                   Symbol("putBoolLn", MType([BoolType()], VoidType())),
                   Symbol("putString", MType([StringType()], VoidType())),
                   Symbol("putStringLn", MType([StringType()], VoidType())),
                   Symbol("putLn", MType([], VoidType()))]

    def __init__(self, ast):
        self.ast = ast

    def convertToSymbol(self, decl):
        if type(decl) == VarDecl:
            return Symbol(decl.variable.name, decl.varType)
        elif type(decl) == FuncDecl:
            return Symbol(decl.name.name, MType([i.varType for i in decl.param], decl.returnType))

    def toListSym(self, listDecl, listSym, kind, listGlobal = None, list_func=None):
        if listGlobal is None:
            for x in listDecl:
                sym = self.convertToSymbol(x)
                res = self.lookup(sym.name, listSym, lambda y: y.name)
                if res is None:
                    listSym.insert(0, sym)
                    if not list_func is None and type(sym.mtype) is MType:
                        list_func.insert(0, sym)
                elif type(sym.mtype) is MType:
                    if type(sym.mtype.rettype) is VoidType:
                        raise Redeclared(Procedure(), sym.name)
                    else:
                        raise Redeclared(Function(), sym.name)
                elif kind == Parameter:
                    raise Redeclared(Parameter(), sym.name)
                else:
                    raise Redeclared(Variable(), sym.name)
        else:
            for x in listDecl:
                sym = self.convertToSymbol(x)
                res = self.lookup(sym.name, listSym, lambda y: y.name)
                res1 = self.lookup(sym.name, listGlobal, lambda y: y.name)
                if res is None and res1 is None:
                    listSym.insert(0, sym)
                    if not list_func is None and type(sym.mtype) is MType:
                        list_func.insert(0, sym)
                elif type(sym.mtype) is MType:
                    if type(sym.mtype.rettype) is VoidType:
                        raise Redeclared(Procedure(), sym.name)
                    else:
                        raise Redeclared(Function(), sym.name)
                elif kind == Parameter:
                    raise Redeclared(Parameter(), sym.name)
                else:
                    raise Redeclared(Variable(), sym.name)

    def checkNoEntryPoint(self, listSym):
        isMain = False
        sym = Symbol("main", MType([], VoidType()))
        for x in listSym:
            if x.name == sym.name and x.mtype.partype == [] and type(x.mtype.rettype) == VoidType:
                isMain = True
                break
        if isMain == False:
            raise NoEntryPoint()

    def checkType(self, left, right):
        if type(left) == type(right):
            if type(left) is ArrayType:
                if type(left.eleType) == type(right.eleType) and left.lower == right.lower and left.upper == right.upper:
                    return True
                else:
                    return False
            else:
                return True
        elif type(left) == FloatType and type(right) == IntType:
            return True
        else:
            return False

    def check(self):
        return self.visit(self.ast, StaticChecker.global_envi)

    def visitProgram(self, ast, c):
        list_func = []
        list_global = []
        self.toListSym(ast.decl, list_global, None, c, list_func)
        self.checkNoEntryPoint(list_global)
        lst = [x for x in ast.decl]
        for x in ast.decl:
            list_func = self.visit(x, (list_global + c, list_func))
        sym = Symbol("main", MType([], VoidType()))
        for x in list_func:
            if not x.name == sym.name or not x.mtype.partype == sym.mtype.partype or not type(x.mtype.rettype) == type(sym.mtype.rettype):
                if type(x.mtype.rettype) is VoidType:
                    raise Unreachable(Procedure(), x.name)
                else:
                    raise Unreachable(Function(), x.name)
        return []

    # Decl
    def visitVarDecl(self, ast, c):
        return c[1]

    def visitFuncDecl(self, ast, c):
        lst = []
        self.toListSym(ast.param, lst, Parameter)
        self.toListSym(ast.local, lst, None)
        func_list = c[1]
        isReturn = False
        for x in ast.body:
            ret = self.visit(x, (lst + c[0], func_list, False, ast.returnType, isReturn))
            isReturn = ret[1]
            func_list = ret[0]
        if not isReturn and not type(ast.returnType) is VoidType:
            raise FunctionNotReturn(ast.name.name)
        return func_list

    # Stmt
    def visitAssign(self, ast, c):
        ret = self.visit(ast.lhs, (c[0], c[1]))
        lhs = ret[0]
        func_list = ret[1]
        if type(lhs) == StringType:
            raise TypeMismatchInStatement(ast)
        if type(lhs) == ArrayType:
            raise TypeMismatchInStatement(ast)
        ret = self.visit(ast.exp, (c[0], func_list))
        exp = ret[0]
        func_list = ret[1]
        if type(exp) == type(lhs):
            pass
        elif type(lhs) == FloatType and type(exp) == IntType:
            pass
        else:
            raise TypeMismatchInStatement(ast)
        if c[4]:
            raise UnreachableStatement(ast)
        return [func_list, c[4]]

    def visitIf(self, ast, c):
        ret = self.visit(ast.expr, (c[0], c[1]))
        expr = ret[0]
        func_list = ret[1]
        if not type(expr) is BoolType:
            raise TypeMismatchInStatement(ast)
        isReturn = False
        for x in ast.thenStmt:
            ret = self.visit(x, (c[0], func_list, c[2], c[3], isReturn))
            func_list = ret[0]
            isReturn = ret[1]
        isReturn1 = False
        for x in ast.elseStmt:
            ret = self.visit(x, (c[0], func_list, c[2], c[3], isReturn1))
            func_list = ret[0]
            isReturn1 = ret[1]
        if c[4]:
            raise UnreachableStatement(ast)
        return [func_list, isReturn and isReturn1]

    def visitWhile(self, ast, c):
        ret = self.visit(ast.exp, (c[0], c[1]))
        exp = ret[0]
        func_list = ret[1]
        if not type(exp) is BoolType:
            raise TypeMismatchInStatement(ast)
        for x in ast.sl:
            func_list = self.visit(x, (c[0], func_list, c[2], c[3], False))[0]
        if c[4]:
            raise UnreachableStatement(ast)
        return [func_list, c[4]]

    def visitFor(self, ast, c):
        ret = self.visit(ast.id, (c[0], c[1]))
        id = ret[0]
        func_list = ret[1]
        if not type(id) is IntType:
            raise TypeMismatchInStatement(ast)
        ret = self.visit(ast.expr1, (c[0], func_list))
        expr1 = ret[0]
        func_list = ret[1]
        if not type(expr1) is IntType:
            raise TypeMismatchInStatement(ast)
        ret = self.visit(ast.expr2, (c[0], func_list))
        expr2 = ret[0]
        func_list = ret[1]
        if not type(expr2) is IntType:
            raise TypeMismatchInStatement(ast)
        isReturn = c[4]
        for x in ast.loop:
            func_list = self.visit(x, (c[0], func_list, c[2], c[3], False))
        if c[4]:
            raise UnreachableStatement(ast)
        return [func_list, isReturn]

    def visitBreak(self, ast, c):
        if c[2] is True:
            pass
        else:
            raise BreakNotInLoop()
        if c[4]:
            raise UnreachableStatement(ast)
        return [c[1], c[4]]

    def visitContinue(self, ast, c):
        if c[2] is True:
            pass
        else:
            raise ContinueNotInLoop()
        if c[4]:
            raise UnreachableStatement(ast)
        return [c[1], c[4]]

    def visitReturn(self, ast, c):
        if not ast.expr is None:
            ret = self.visit(ast.expr, (c[0], c[1]))
            expr = ret[0]
            func_list = ret[1]
            if expr is None and type(c[3]) is VoidType:
                pass
            if not self.checkType(c[3], expr):
                raise TypeMismatchInStatement(ast)
            if c[4]:
                raise UnreachableStatement(ast)
            return [func_list, True]
        else:
            if c[4]:
                raise UnreachableStatement(ast)
            return [c[1], True]

    def visitWith(self, ast, c):
        lst = []
        self.toListSym(ast.decl, lst, None)
        # list(map(lambda x: self.visit(x, (lst + c[0], c[1], c[2], c[3])), ast.stmt))
        func_list = c[1]
        isReturn = c[4]
        for x in ast.stmt:
            ret = self.visit(x, (lst + c[0], func_list, c[2], c[3], isReturn))
            func_list = ret[0]
            isReturn = ret[1]
        if c[4]:
            raise UnreachableStatement(ast)
        return [func_list, isReturn]

    def visitCallStmt(self, ast, c):
        at = []
        func_list = c[1]
        for x in ast.param:
            ret = self.visit(x, (c[0], func_list))
            at.append(ret[0])
            func_list = ret[1]
        res = self.lookup(ast.method.name, c[0], lambda x: x.name)
        if res is None or not type(res.mtype) is MType or not type(res.mtype.rettype) is VoidType:
            raise Undeclared(Procedure(), ast.method.name)
        elif len(res.mtype.partype) != len(at):
            raise TypeMismatchInStatement(ast)
        else:
            for i in range(len(res.mtype.partype)):
                if not self.checkType(res.mtype.partype[i], at[i]):
                    raise TypeMismatchInStatement(ast)
        func_list_ret = []
        for x in func_list:
            if not ast.method.name == x.name:
                func_list_ret.append(x)
        if c[4]:
            raise UnreachableStatement(ast)
        return [func_list_ret, c[4]]

    # Expression
    def visitBinaryOp(self, ast, c):
        ret = self.visit(ast.left, (c[0], c[1]))
        left = ret[0]
        func_list = ret[1]
        ret = self.visit(ast.right, (c[0], func_list))
        right = ret[0]
        func_list = ret[1]

        if type(left) == type(right):
            if type(left) is BoolType and ast.op in ['and', 'andthen', 'or', 'orelse']:
                return [BoolType(), func_list]
            elif type(left) is IntType:
                if ast.op in ['+', '-', '*', 'div', 'mod']:
                    return [IntType(), func_list]
                elif ast.op in ['<', '<=', '>', '>=', '<>', '=']:
                    return [BoolType(), func_list]
                elif ast.op == '/':
                    return [FloatType(), func_list]
            elif type(left) is FloatType:
                if ast.op in ['+', '-', '*', '/']:
                    return [FloatType(), func_list]
                elif ast.op in ['=', '<>', '<', '<=', '>', '>=']:
                    return [BoolType(), func_list]
            else:
                raise TypeMismatchInExpression(ast)
        else:
            if type(left) is IntType and type(right) is FloatType:
                return [FloatType(), func_list]
            elif type(left) is FloatType and type(right) is IntType:
                return [FloatType(), func_list]
            else:
                raise TypeMismatchInExpression(ast)

    def visitUnaryOp(self, ast, c):
        ret = self.visit(ast.body, (c[0], c[1]))
        expr = ret[0]
        func_list = ret[1]
        if ast.op == '-' and type(expr) is BoolType:
            return [BoolType(), func_list]
        elif ast.op == '-' and type(expr) is IntType:
            return [IntType(). func_list]
        elif ast.op == '-' and type(expr) is FloatType:
            return [FloatType(), func_list]
        else:
            raise TypeMismatchInExpression(ast)

    def visitCallExpr(self, ast, c):
        at = []
        func_list = c[1]
        for x in ast.param:
            ret = self.visit(x, (c[0], func_list))
            at.append(ret[0])
            func_list = ret[1]
        res = self.lookup(ast.method.name, c[0], lambda x: x.name)
        if res is None or not type(res.mtype) is MType or type(res.mtype.rettype) is VoidType:
            raise Undeclared(Procedure(), ast.method.name)
        elif len(res.mtype.partype) != len(at):
            raise TypeMismatchInExpression(ast)
        else:
            for i in range(len(res.mtype.partype)):
                if not self.checkType(res.mtype.partype[i], at[i]):
                    raise TypeMismatchInExpression(ast)
        func_list_ret = []
        for x in func_list:
            if not ast.method.name == x.name:
                func_list_ret.append(x)
        return [res.mtype.rettype, func_list_ret]

    # LHS
    def visitId(self, ast, c):
        res = self.lookup(ast.name, c[0], lambda x: x.name)
        if res is None:
            raise Undeclared(Identifier(), ast.name)
        elif type(res.mtype) is MType:
            raise Undeclared(Identifier(), ast.name)
        else:
            return [res.mtype, c[1]]

    def visitArrayCell(self, ast, c):
        ret = self.visit(ast.arr, (c[0], c[1]))
        arr = ret[0]
        func_list = ret[1]
        if not type(arr) is ArrayType:
            raise TypeMismatchInExpression(ast)
        ret = self.visit(ast.idx, (c[0], func_list))
        idx = ret[0]
        func_list = ret[1]
        if not type(idx) is IntType:
            raise TypeMismatchInExpression(ast)
        return [arr.eleType, func_list]

    def visitIntLiteral(self, ast, c):
        return [IntType(), c[1]]

    def visitFloatLiteral(self, ast, c):
        return [FloatType(), c[1]]

    def visitBooleanLiteral(self, ast, c):
        return [BoolType(), c[1]]

    def visitStringLiteral(self, ast, c):
        return [StringType(), c[1]]

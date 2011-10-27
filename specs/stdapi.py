##########################################################################
#
# Copyright 2008-2010 VMware, Inc.
# All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
##########################################################################/

"""C basic types"""


import debug


class Type:
    """Base class for all types."""

    __tags = set()

    def __init__(self, expr, tag = None):
        self.expr = expr

        # Generate a default tag, used when naming functions that will operate
        # on this type, so it should preferrably be something representative of
        # the type.
        if tag is None:
            tag = ''.join([c for c in expr if c.isalnum() or c in '_'])
        else:
            for c in tag:
                assert c.isalnum() or c in '_'

        # Ensure it is unique.
        if tag in Type.__tags:
            suffix = 1
            while tag + str(suffix) in Type.__tags:
                suffix += 1
            tag += str(suffix)

        assert tag not in Type.__tags
        Type.__tags.add(tag)

        self.tag = tag

    def __str__(self):
        """Return the C/C++ type expression for this type."""
        return self.expr

    def visit(self, visitor, *args, **kwargs):
        raise NotImplementedError



class _Void(Type):
    """Singleton void type."""

    def __init__(self):
        Type.__init__(self, "void")

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_void(self, *args, **kwargs)

Void = _Void()


class Literal(Type):
    """Class to describe literal types.

    Types which are not defined in terms of other types, such as integers and
    floats."""

    def __init__(self, expr, kind):
        Type.__init__(self, expr)
        self.kind = kind

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_literal(self, *args, **kwargs)


class Const(Type):

    def __init__(self, type):
        # While "const foo" and "foo const" are synonymous, "const foo *" and
        # "foo * const" are not quite the same, and some compilers do enforce
        # strict const correctness.
        if isinstance(type, String) or type is WString:
            # For strings we never intend to say a const pointer to chars, but
            # rather a point to const chars.
            expr = "const " + type.expr
        elif type.expr.startswith("const ") or '*' in type.expr:
            expr = type.expr + " const"
        else:
            # The most legible
            expr = "const " + type.expr

        Type.__init__(self, expr, 'C' + type.tag)

        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_const(self, *args, **kwargs)


class Pointer(Type):

    def __init__(self, type):
        Type.__init__(self, type.expr + " *", 'P' + type.tag)
        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_pointer(self, *args, **kwargs)


class Handle(Type):

    def __init__(self, name, type, range=None, key=None):
        Type.__init__(self, type.expr, 'P' + type.tag)
        self.name = name
        self.type = type
        self.range = range
        self.key = key

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_handle(self, *args, **kwargs)


def ConstPointer(type):
    return Pointer(Const(type))


class Enum(Type):

    __id = 0

    def __init__(self, name, values):
        Type.__init__(self, name)

        self.id = Enum.__id
        Enum.__id += 1

        self.values = list(values)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_enum(self, *args, **kwargs)


def FakeEnum(type, values):
    return Enum(type.expr, values)


class Bitmask(Type):

    __id = 0

    def __init__(self, type, values):
        Type.__init__(self, type.expr)

        self.id = Bitmask.__id
        Bitmask.__id += 1

        self.type = type
        self.values = values

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_bitmask(self, *args, **kwargs)

Flags = Bitmask


class Array(Type):

    def __init__(self, type, length):
        Type.__init__(self, type.expr + " *")
        self.type = type
        self.length = length

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_array(self, *args, **kwargs)


class Blob(Type):

    def __init__(self, type, size):
        Type.__init__(self, type.expr + ' *')
        self.type = type
        self.size = size

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_blob(self, *args, **kwargs)


class Struct(Type):

    __id = 0

    def __init__(self, name, members):
        Type.__init__(self, name)

        self.id = Struct.__id
        Struct.__id += 1

        self.name = name
        self.members = members

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_struct(self, *args, **kwargs)


class Alias(Type):

    def __init__(self, expr, type):
        Type.__init__(self, expr)
        self.type = type

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_alias(self, *args, **kwargs)


def Out(type, name):
    arg = Arg(type, name, output=True)
    return arg


class Arg:

    def __init__(self, type, name, output=False):
        self.type = type
        self.name = name
        self.output = output
        self.index = None

    def __str__(self):
        return '%s %s' % (self.type, self.name)


class Function:

    # 0-3 are reserved to memcpy, malloc, free, and realloc
    __id = 4

    def __init__(self, type, name, args, call = '', fail = None, sideeffects=True):
        self.id = Function.__id
        Function.__id += 1

        self.type = type
        self.name = name

        self.args = []
        index = 0
        for arg in args:
            if not isinstance(arg, Arg):
                if isinstance(arg, tuple):
                    arg_type, arg_name = arg
                else:
                    arg_type = arg
                    arg_name = "arg%u" % index
                arg = Arg(arg_type, arg_name)
            arg.index = index
            index += 1
            self.args.append(arg)

        self.call = call
        self.fail = fail
        self.sideeffects = sideeffects

    def prototype(self, name=None):
        if name is not None:
            name = name.strip()
        else:
            name = self.name
        s = name
        if self.call:
            s = self.call + ' ' + s
        if name.startswith('*'):
            s = '(' + s + ')'
        s = self.type.expr + ' ' + s
        s += "("
        if self.args:
            s += ", ".join(["%s %s" % (arg.type, arg.name) for arg in self.args])
        else:
            s += "void"
        s += ")"
        return s


def StdFunction(*args, **kwargs):
    kwargs.setdefault('call', '__stdcall')
    return Function(*args, **kwargs)


def FunctionPointer(type, name, args, **kwargs):
    # XXX: We should probably treat function pointers (callbacks or not) in a generic fashion
    return Opaque(name)


class Interface(Type):

    def __init__(self, name, base=None):
        Type.__init__(self, name)
        self.name = name
        self.base = base
        self.methods = []

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_interface(self, *args, **kwargs)

    def itermethods(self):
        if self.base is not None:
            for method in self.base.itermethods():
                yield method
        for method in self.methods:
            yield method
        raise StopIteration


class Method(Function):

    def __init__(self, type, name, args):
        Function.__init__(self, type, name, args, call = '__stdcall')
        for index in range(len(self.args)):
            self.args[index].index = index + 1


class String(Type):

    def __init__(self, expr = "char *", length = None, kind = 'String'):
        Type.__init__(self, expr)
        self.length = length
        self.kind = kind

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_string(self, *args, **kwargs)


class Opaque(Type):
    '''Opaque pointer.'''

    def __init__(self, expr):
        Type.__init__(self, expr)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_opaque(self, *args, **kwargs)


def OpaquePointer(type, *args):
    return Opaque(type.expr + ' *')

def OpaqueArray(type, size):
    return Opaque(type.expr + ' *')

def OpaqueBlob(type, size):
    return Opaque(type.expr + ' *')


class Polymorphic(Type):

    def __init__(self, default_type, switch_expr, switch_types):
        Type.__init__(self, default_type.expr)
        self.default_type = default_type
        self.switch_expr = switch_expr
        self.switch_types = switch_types

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_polymorphic(self, *args, **kwargs)

    def iterswitch(self):
        cases = [['default']]
        types = [self.default_type]

        for expr, type in self.switch_types:
            case = 'case %s' % expr
            try:
                i = types.index(type)
            except ValueError:
                cases.append([case])
                types.append(type)
            else:
                cases[i].append(case)

        return zip(cases, types)


class Visitor:

    def visit(self, type, *args, **kwargs):
        return type.visit(self, *args, **kwargs)

    def visit_void(self, void, *args, **kwargs):
        raise NotImplementedError

    def visit_literal(self, literal, *args, **kwargs):
        raise NotImplementedError

    def visit_string(self, string, *args, **kwargs):
        raise NotImplementedError

    def visit_const(self, const, *args, **kwargs):
        raise NotImplementedError

    def visit_struct(self, struct, *args, **kwargs):
        raise NotImplementedError

    def visit_array(self, array, *args, **kwargs):
        raise NotImplementedError

    def visit_blob(self, blob, *args, **kwargs):
        raise NotImplementedError

    def visit_enum(self, enum, *args, **kwargs):
        raise NotImplementedError

    def visit_bitmask(self, bitmask, *args, **kwargs):
        raise NotImplementedError

    def visit_pointer(self, pointer, *args, **kwargs):
        raise NotImplementedError

    def visit_handle(self, handle, *args, **kwargs):
        raise NotImplementedError

    def visit_alias(self, alias, *args, **kwargs):
        raise NotImplementedError

    def visit_opaque(self, opaque, *args, **kwargs):
        raise NotImplementedError

    def visit_interface(self, interface, *args, **kwargs):
        raise NotImplementedError

    def visit_polymorphic(self, polymorphic, *args, **kwargs):
        raise NotImplementedError
        #return self.visit(polymorphic.default_type, *args, **kwargs)


class OnceVisitor(Visitor):

    def __init__(self):
        self.__visited = set()

    def visit(self, type, *args, **kwargs):
        if type not in self.__visited:
            self.__visited.add(type)
            return type.visit(self, *args, **kwargs)
        return None


class Rebuilder(Visitor):

    def visit_void(self, void):
        return void

    def visit_literal(self, literal):
        return literal

    def visit_string(self, string):
        return string

    def visit_const(self, const):
        return Const(const.type)

    def visit_struct(self, struct):
        members = [(self.visit(type), name) for type, name in struct.members]
        return Struct(struct.name, members)

    def visit_array(self, array):
        type = self.visit(array.type)
        return Array(type, array.length)

    def visit_blob(self, blob):
        type = self.visit(blob.type)
        return Blob(type, blob.size)

    def visit_enum(self, enum):
        return enum

    def visit_bitmask(self, bitmask):
        type = self.visit(bitmask.type)
        return Bitmask(type, bitmask.values)

    def visit_pointer(self, pointer):
        type = self.visit(pointer.type)
        return Pointer(type)

    def visit_handle(self, handle):
        type = self.visit(handle.type)
        return Handle(handle.name, type, range=handle.range, key=handle.key)

    def visit_alias(self, alias):
        type = self.visit(alias.type)
        return Alias(alias.expr, type)

    def visit_opaque(self, opaque):
        return opaque

    def visit_polymorphic(self, polymorphic):
        default_type = self.visit(polymorphic.default_type)
        switch_expr = polymorphic.switch_expr
        switch_types = [(expr, self.visit(type)) for expr, type in polymorphic.switch_types]
        return Polymorphic(default_type, switch_expr, switch_types)


class Collector(Visitor):
    '''Collect.'''

    def __init__(self):
        self.__visited = set()
        self.types = []

    def visit(self, type):
        if type in self.__visited:
            return
        self.__visited.add(type)
        Visitor.visit(self, type)
        self.types.append(type)

    def visit_void(self, literal):
        pass

    def visit_literal(self, literal):
        pass

    def visit_string(self, string):
        pass

    def visit_const(self, const):
        self.visit(const.type)

    def visit_struct(self, struct):
        for type, name in struct.members:
            self.visit(type)

    def visit_array(self, array):
        self.visit(array.type)

    def visit_blob(self, array):
        pass

    def visit_enum(self, enum):
        pass

    def visit_bitmask(self, bitmask):
        self.visit(bitmask.type)

    def visit_pointer(self, pointer):
        self.visit(pointer.type)

    def visit_handle(self, handle):
        self.visit(handle.type)

    def visit_alias(self, alias):
        self.visit(alias.type)

    def visit_opaque(self, opaque):
        pass

    def visit_interface(self, interface):
        if interface.base is not None:
            self.visit(interface.base)
        for method in interface.itermethods():
            for arg in method.args:
                self.visit(arg.type)
            self.visit(method.type)

    def visit_polymorphic(self, polymorphic):
        self.visit(polymorphic.default_type)
        for expr, type in polymorphic.switch_types:
            self.visit(type)


class API:

    def __init__(self, name = None):
        self.name = name
        self.headers = []
        self.functions = []
        self.interfaces = []

    def all_types(self):
        collector = Collector()
        for function in self.functions:
            for arg in function.args:
                collector.visit(arg.type)
            collector.visit(function.type)
        for interface in self.interfaces:
            collector.visit(interface)
            for method in interface.itermethods():
                for arg in method.args:
                    collector.visit(arg.type)
                collector.visit(method.type)
        return collector.types

    def add_function(self, function):
        self.functions.append(function)

    def add_functions(self, functions):
        for function in functions:
            self.add_function(function)

    def add_interface(self, interface):
        self.interfaces.append(interface)

    def add_interfaces(self, interfaces):
        self.interfaces.extend(interfaces)

    def add_api(self, api):
        self.headers.extend(api.headers)
        self.add_functions(api.functions)
        self.add_interfaces(api.interfaces)

    def get_function_by_name(self, name):
        for function in self.functions:
            if function.name == name:
                return function
        return None


Bool = Literal("bool", "Bool")
SChar = Literal("signed char", "SInt")
UChar = Literal("unsigned char", "UInt")
Short = Literal("short", "SInt")
Int = Literal("int", "SInt")
Long = Literal("long", "SInt")
LongLong = Literal("long long", "SInt")
UShort = Literal("unsigned short", "UInt")
UInt = Literal("unsigned int", "UInt")
ULong = Literal("unsigned long", "UInt")
ULongLong = Literal("unsigned long long", "UInt")
Float = Literal("float", "Float")
Double = Literal("double", "Double")
SizeT = Literal("size_t", "UInt")

# C string (i.e., zero terminated)
CString = String()
WString = String("wchar_t *", kind="WString")

Int8 = Literal("int8_t", "SInt")
UInt8 = Literal("uint8_t", "UInt")
Int16 = Literal("int16_t", "SInt")
UInt16 = Literal("uint16_t", "UInt")
Int32 = Literal("int32_t", "SInt")
UInt32 = Literal("uint32_t", "UInt")
Int64 = Literal("int64_t", "SInt")
UInt64 = Literal("uint64_t", "UInt")

##########################################################################
#
# Copyright 2011 Jose Fonseca
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


'''Generate code to dump most GL state into JSON.'''


from specs.stdapi import *

from specs.gltypes import *
from specs.glparams import *


texture_targets = [
    ('GL_TEXTURE_1D', 'GL_TEXTURE_BINDING_1D'),
    ('GL_TEXTURE_2D', 'GL_TEXTURE_BINDING_2D'),
    ('GL_TEXTURE_3D', 'GL_TEXTURE_BINDING_3D'),
    ('GL_TEXTURE_RECTANGLE', 'GL_TEXTURE_BINDING_RECTANGLE'),
    ('GL_TEXTURE_CUBE_MAP', 'GL_TEXTURE_BINDING_CUBE_MAP')
]

framebuffer_targets = [
    ('GL_DRAW_FRAMEBUFFER', 'GL_DRAW_FRAMEBUFFER_BINDING'),
    ('GL_READ_FRAMEBUFFER', 'GL_READ_FRAMEBUFFER_BINDING'),
]

class GetInflector:
    '''Objects that describes how to inflect.'''

    reduced_types = {
        B: I,
        E: I,
        I: F,
    }

    def __init__(self, radical, inflections, suffix = ''):
        self.radical = radical
        self.inflections = inflections
        self.suffix = suffix

    def reduced_type(self, type):
        if type in self.inflections:
            return type
        if type in self.reduced_types:
            return self.reduced_type(self.reduced_types[type])
        raise NotImplementedError

    def inflect(self, type):
        return self.radical + self.inflection(type) + self.suffix

    def inflection(self, type):
        type = self.reduced_type(type)
        assert type in self.inflections
        return self.inflections[type]

    def __str__(self):
        return self.radical + self.suffix


class StateGetter(Visitor):
    '''Type visitor that is able to extract the state via one of the glGet*
    functions.

    It will declare any temporary variable
    '''

    def __init__(self, radical, inflections, suffix=''):
        self.inflector = GetInflector(radical, inflections)
        self.suffix = suffix

    def __call__(self, *args):
        pname = args[-1]

        for function, type, count, name in parameters:
            if type is X:
                continue
            if name == pname:
                if count != 1:
                    type = Array(type, str(count))

                return type, self.visit(type, args)

        raise NotImplementedError

    def temp_name(self, args):
        '''Return the name of a temporary variable to hold the state.'''
        pname = args[-1]

        return pname[3:].lower()

    def visit_const(self, const, args):
        return self.visit(const.type, args)

    def visit_scalar(self, type, args):
        temp_name = self.temp_name(args)
        elem_type = self.inflector.reduced_type(type)
        inflection = self.inflector.inflect(type)
        if inflection.endswith('v'):
            print '    %s %s = 0;' % (elem_type, temp_name)
            print '    %s(%s, &%s);' % (inflection + self.suffix, ', '.join(args), temp_name)
        else:
            print '    %s %s = %s(%s);' % (elem_type, temp_name, inflection + self.suffix, ', '.join(args))
        return temp_name

    def visit_string(self, string, args):
        temp_name = self.temp_name(args)
        inflection = self.inflector.inflect(string)
        assert not inflection.endswith('v')
        print '    %s %s = (%s)%s(%s);' % (string, temp_name, string, inflection + self.suffix, ', '.join(args))
        return temp_name

    def visit_alias(self, alias, args):
        return self.visit_scalar(alias, args)

    def visit_enum(self, enum, args):
        return self.visit(GLint, args)

    def visit_bitmask(self, bitmask, args):
        return self.visit(GLint, args)

    def visit_array(self, array, args):
        temp_name = self.temp_name(args)
        if array.length == '1':
            return self.visit(array.type)
        elem_type = self.inflector.reduced_type(array.type)
        inflection = self.inflector.inflect(array.type)
        assert inflection.endswith('v')
        print '    %s %s[%s];' % (elem_type, temp_name, array.length)
        print '    memset(%s, 0, %s * sizeof *%s);' % (temp_name, array.length, temp_name)
        print '    %s(%s, %s);' % (inflection + self.suffix, ', '.join(args), temp_name)
        return temp_name

    def visit_opaque(self, pointer, args):
        temp_name = self.temp_name(args)
        inflection = self.inflector.inflect(pointer)
        assert inflection.endswith('v')
        print '    GLvoid *%s;' % temp_name
        print '    %s(%s, &%s);' % (inflection + self.suffix, ', '.join(args), temp_name)
        return temp_name


glGet = StateGetter('glGet', {
    B: 'Booleanv',
    I: 'Integerv',
    F: 'Floatv',
    D: 'Doublev',
    S: 'String',
    P: 'Pointerv',
})

glGetMaterial = StateGetter('glGetMaterial', {I: 'iv', F: 'fv'})
glGetLight = StateGetter('glGetLight', {I: 'iv', F: 'fv'})
glGetVertexAttrib = StateGetter('glGetVertexAttrib', {I: 'iv', F: 'fv', D: 'dv', P: 'Pointerv'})
glGetTexParameter = StateGetter('glGetTexParameter', {I: 'iv', F: 'fv'})
glGetTexEnv = StateGetter('glGetTexEnv', {I: 'iv', F: 'fv'})
glGetTexLevelParameter = StateGetter('glGetTexLevelParameter', {I: 'iv', F: 'fv'})
glGetShader = StateGetter('glGetShaderiv', {I: 'iv'})
glGetProgram = StateGetter('glGetProgram', {I: 'iv'})
glGetProgramARB = StateGetter('glGetProgram', {I: 'iv', F: 'fv', S: 'Stringv'}, 'ARB')
glGetFramebufferAttachmentParameter = StateGetter('glGetFramebufferAttachmentParameter', {I: 'iv'})


class JsonWriter(Visitor):
    '''Type visitor that will dump a value of the specified type through the
    JSON writer.
    
    It expects a previously declared JSONWriter instance named "json".'''

    def visit_literal(self, literal, instance):
        if literal.kind == 'Bool':
            print '    json.writeBool(%s);' % instance
        elif literal.kind in ('SInt', 'Uint', 'Float', 'Double'):
            print '    json.writeNumber(%s);' % instance
        else:
            raise NotImplementedError

    def visit_string(self, string, instance):
        assert string.length is None
        print '    json.writeString((const char *)%s);' % instance

    def visit_enum(self, enum, instance):
        if enum.expr == 'GLenum':
            print '    dumpEnum(json, %s);' % instance
        else:
            print '    json.writeNumber(%s);' % instance

    def visit_bitmask(self, bitmask, instance):
        raise NotImplementedError

    def visit_alias(self, alias, instance):
        self.visit(alias.type, instance)

    def visit_opaque(self, opaque, instance):
        print '    json.writeNumber((size_t)%s);' % instance

    __index = 0

    def visit_array(self, array, instance):
        index = '__i%u' % JsonWriter.__index
        JsonWriter.__index += 1
        print '    json.beginArray();'
        print '    for (unsigned %s = 0; %s < %s; ++%s) {' % (index, index, array.length, index)
        self.visit(array.type, '%s[%s]' % (instance, index))
        print '    }'
        print '    json.endArray();'



class StateDumper:
    '''Class to generate code to dump all GL state in JSON format via
    stdout.'''

    def __init__(self):
        pass

    def dump(self):
        print '#include <string.h>'
        print
        print '#include "json.hpp"'
        print '#include "glproc.hpp"'
        print '#include "glsize.hpp"'
        print '#include "glstate.hpp"'
        print
        print 'namespace glstate {'
        print

        print 'const char *'
        print 'enumToString(GLenum pname)'
        print '{'
        print '    switch (pname) {'
        n = len(GLenum.values)
        for i in xrange(n):
            value = GLenum.values[i]
            name = value
            if GLenum.pretty_names.has_key(value):
                name = GLenum.pretty_names[value]
            print '    case %s:' % value
            print '        return "%s";' % name
        print '    default:'
        print '        return NULL;'
        print '    }'
        print '}'
        print

        print 'static void'
        print 'dumpFramebufferAttachementParameters(JSONWriter &json, GLenum target, GLenum attachment)'
        print '{'
        self.dump_attachment_parameters('target', 'attachment')
        print '}'
        print

        print 'void'
        print 'dumpEnum(JSONWriter &json, GLenum pname)'
        print '{'
        print '    const char *s = enumToString(pname);'
        print '    if (s) {'
        print '        json.writeString(s);'
        print '    } else {'
        print '        json.writeNumber(pname);'
        print '    }'
        print '}'
        print

        print 'void dumpParameters(JSONWriter &json)'
        print '{'
        print '    json.beginMember("parameters");'
        print '    json.beginObject();'
        
        self.dump_atoms(glGet)
        
        self.dump_material_params()
        self.dump_light_params()
        self.dump_vertex_attribs()
        self.dump_texenv_params()
        self.dump_program_params()
        self.dump_texture_parameters()
        self.dump_framebuffer_parameters()

        print '    json.endObject();'
        print '    json.endMember(); // parameters'
        print '}'
        print
        
        print '} /*namespace glstate */'

    def dump_material_params(self):
        for face in ['GL_FRONT', 'GL_BACK']:
            print '    json.beginMember("%s");' % face
            print '    json.beginObject();'
            self.dump_atoms(glGetMaterial, face)
            print '    json.endObject();'
        print

    def dump_light_params(self):
        print '    GLint max_lights = 0;'
        print '    __glGetIntegerv(GL_MAX_LIGHTS, &max_lights);'
        print '    for (GLint index = 0; index < max_lights; ++index) {'
        print '        GLenum light = GL_LIGHT0 + index;'
        print '        if (glIsEnabled(light)) {'
        print '            char name[32];'
        print '            snprintf(name, sizeof name, "GL_LIGHT%i", index);'
        print '            json.beginMember(name);'
        print '            json.beginObject();'
        self.dump_atoms(glGetLight, '    GL_LIGHT0 + index')
        print '            json.endObject();'
        print '            json.endMember(); // GL_LIGHTi'
        print '        }'
        print '    }'
        print

    def dump_texenv_params(self):
        for target in ['GL_TEXTURE_ENV', 'GL_TEXTURE_FILTER_CONTROL', 'GL_POINT_SPRITE']:
            if target != 'GL_TEXTURE_FILTER_CONTROL':
                print '    if (glIsEnabled(%s)) {' % target
            else:
                print '    {'
            print '        json.beginMember("%s");' % target
            print '        json.beginObject();'
            self.dump_atoms(glGetTexEnv, target)
            print '        json.endObject();'
            print '    }'

    def dump_vertex_attribs(self):
        print '    GLint max_vertex_attribs = 0;'
        print '    __glGetIntegerv(GL_MAX_VERTEX_ATTRIBS, &max_vertex_attribs);'
        print '    for (GLint index = 0; index < max_vertex_attribs; ++index) {'
        print '        char name[32];'
        print '        snprintf(name, sizeof name, "GL_VERTEX_ATTRIB_ARRAY%i", index);'
        print '        json.beginMember(name);'
        print '        json.beginObject();'
        self.dump_atoms(glGetVertexAttrib, 'index')
        print '        json.endObject();'
        print '        json.endMember(); // GL_VERTEX_ATTRIB_ARRAYi'
        print '    }'
        print

    program_targets = [
        'GL_FRAGMENT_PROGRAM_ARB',
        'GL_VERTEX_PROGRAM_ARB',
    ]

    def dump_program_params(self):
        for target in self.program_targets:
            print '    if (glIsEnabled(%s)) {' % target
            print '        json.beginMember("%s");' % target
            print '        json.beginObject();'
            self.dump_atoms(glGetProgramARB, target)
            print '        json.endObject();'
            print '    }'

    def dump_texture_parameters(self):
        print '    {'
        print '        GLint active_texture = GL_TEXTURE0;'
        print '        glGetIntegerv(GL_ACTIVE_TEXTURE, &active_texture);'
        print '        GLint max_texture_coords = 0;'
        print '        glGetIntegerv(GL_MAX_TEXTURE_COORDS, &max_texture_coords);'
        print '        GLint max_combined_texture_image_units = 0;'
        print '        glGetIntegerv(GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS, &max_combined_texture_image_units);'
        print '        GLint max_units = std::max(max_combined_texture_image_units, max_texture_coords);'
        print '        for (GLint unit = 0; unit < max_units; ++unit) {'
        print '            char name[32];'
        print '            snprintf(name, sizeof name, "GL_TEXTURE%i", unit);'
        print '            json.beginMember(name);'
        print '            glActiveTexture(GL_TEXTURE0 + unit);'
        print '            json.beginObject();'
        print '            GLboolean enabled;'
        print '            GLint binding;'
        print
        for target, binding in texture_targets:
            print '            // %s' % target
            print '            enabled = GL_FALSE;'
            print '            glGetBooleanv(%s, &enabled);' % target
            print '            json.writeBoolMember("%s", enabled);' % target
            print '            binding = 0;'
            print '            glGetIntegerv(%s, &binding);' % binding
            print '            json.writeNumberMember("%s", binding);' % binding
            print '            if (enabled || binding) {'
            print '                json.beginMember("%s");' % target
            print '                json.beginObject();'
            self.dump_atoms(glGetTexParameter, target)
            # We only dump the first level parameters
            self.dump_atoms(glGetTexLevelParameter, target, "0")
            print '                json.endObject();'
            print '                json.endMember(); // %s' % target
            print '            }'
            print
        print '            json.endObject();'
        print '            json.endMember(); // GL_TEXTUREi'
        print '        }'
        print '        glActiveTexture(active_texture);'
        print '    }'
        print

    def dump_framebuffer_parameters(self):
        print '    {'
        print '        GLint max_color_attachments = 0;'
        print '        glGetIntegerv(GL_MAX_COLOR_ATTACHMENTS, &max_color_attachments);'
        print '        GLint framebuffer;'
        for target, binding in framebuffer_targets:
            print '            // %s' % target
            print '            framebuffer = 0;'
            print '            glGetIntegerv(%s, &framebuffer);' % binding
            print '            if (framebuffer) {'
            print '                json.beginMember("%s");' % target
            print '                json.beginObject();'
            print '                for (GLint i = 0; i < max_color_attachments; ++i) {'
            print '                    GLint color_attachment = GL_COLOR_ATTACHMENT0 + i;'
            print '                    dumpFramebufferAttachementParameters(json, %s, color_attachment);' % target
            print '                }'
            print '                dumpFramebufferAttachementParameters(json, %s, GL_DEPTH_ATTACHMENT);' % target
            print '                dumpFramebufferAttachementParameters(json, %s, GL_STENCIL_ATTACHMENT);' % target
            print '                json.endObject();'
            print '                json.endMember(); // %s' % target
            print '            }'
            print
        print '    }'
        print

    def dump_attachment_parameters(self, target, attachment):
        print '            {'
        print '                GLint object_type = GL_NONE;'
        print '                glGetFramebufferAttachmentParameteriv(%s, %s, GL_FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE, &object_type);' % (target, attachment)
        print '                if (object_type != GL_NONE) {'
        print '                    json.beginMember(enumToString(%s));' % attachment
        print '                    json.beginObject();'
        self.dump_atoms(glGetFramebufferAttachmentParameter, target, attachment)
        print '                    json.endObject();'
        print '                    json.endMember(); // GL_x_ATTACHMENT'
        print '                }'
        print '            }'

    def dump_atoms(self, getter, *args):
        for function, type, count, name in parameters:
            inflection = getter.inflector.radical + getter.suffix
            if inflection not in function.split(','):
                continue
            if type is X:
                continue
            print '        // %s' % name
            print '        {'
            type, value = getter(*(args + (name,)))
            print '            if (glGetError() != GL_NO_ERROR) {'
            #print '                std::cerr << "warning: %s(%s) failed\\n";' % (inflection, name)
            print '            } else {'
            print '                json.beginMember("%s");' % name
            JsonWriter().visit(type, value)
            print '                json.endMember();'
            print '            }'
            print '        }'
            print


if __name__ == '__main__':
    StateDumper().dump()

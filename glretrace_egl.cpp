/**************************************************************************
 *
 * Copyright 2011 LunarG, Inc.
 * All Rights Reserved.
 *
 * Based on glretrace_glx.cpp, which has
 *
 *   Copyright 2011 Jose Fonseca
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 **************************************************************************/


#include "glproc.hpp"
#include "retrace.hpp"
#include "glretrace.hpp"
#include "os.hpp"

#ifndef EGL_OPENGL_ES_API
#define EGL_OPENGL_ES_API		0x30A0
#define EGL_OPENVG_API			0x30A1
#define EGL_OPENGL_API			0x30A2
#endif


using namespace glretrace;


typedef std::map<unsigned long long, glws::Drawable *> DrawableMap;
typedef std::map<unsigned long long, glws::Context *> ContextMap;
static DrawableMap drawable_map;
static ContextMap context_map;

static unsigned int current_api = EGL_OPENGL_ES_API;

static glws::Drawable *
getDrawable(unsigned long long surface_ptr) {
    if (surface_ptr == 0) {
        return NULL;
    }

    DrawableMap::const_iterator it;
    it = drawable_map.find(surface_ptr);

    return (it != drawable_map.end()) ? it->second : NULL;
}

static glws::Context *
getContext(unsigned long long context_ptr) {
    if (context_ptr == 0) {
        return NULL;
    }

    ContextMap::const_iterator it;
    it = context_map.find(context_ptr);

    return (it != context_map.end()) ? it->second : NULL;
}

static void retrace_eglCreateWindowSurface(trace::Call &call) {
    unsigned long long orig_surface = call.ret->toUIntPtr();

    glws::Drawable *drawable = glws::createDrawable(glretrace::visual);
    drawable_map[orig_surface] = drawable;
}

static void retrace_eglDestroySurface(trace::Call &call) {
    unsigned long long orig_surface = call.arg(1).toUIntPtr();

    DrawableMap::iterator it;
    it = drawable_map.find(orig_surface);

    if (it != drawable_map.end()) {
        delete it->second;
        drawable_map.erase(it);
    }
}

static void retrace_eglBindAPI(trace::Call &call) {
    current_api = call.arg(0).toUInt();
}

static void retrace_eglCreateContext(trace::Call &call) {
    if (current_api != EGL_OPENGL_API) {
        retrace::warning(call) << "only OpenGL is supported.  Aborting...\n";
        os::abort();
        return;
    }

    unsigned long long orig_context = call.ret->toUIntPtr();
    glws::Context *share_context = getContext(call.arg(2).toUIntPtr());

    glws::Context *context = glws::createContext(glretrace::visual, share_context);
    context_map[orig_context] = context;
}

static void retrace_eglDestroyContext(trace::Call &call) {
    unsigned long long orig_context = call.arg(1).toUIntPtr();

    ContextMap::iterator it;
    it = context_map.find(orig_context);

    if (it != context_map.end()) {
        delete it->second;
        context_map.erase(it);
    }
}

static void retrace_eglMakeCurrent(trace::Call &call) {
    glws::Drawable *new_drawable = getDrawable(call.arg(1).toUIntPtr());
    glws::Context *new_context = getContext(call.arg(3).toUIntPtr());

    if (new_drawable == drawable && new_context == context) {
        return;
    }

    if (drawable && context) {
        glFlush();
        if (!double_buffer) {
            frame_complete(call);
        }
    }

    bool result = glws::makeCurrent(new_drawable, new_context);

    if (new_drawable && new_context && result) {
        drawable = new_drawable;
        context = new_context;
    } else {
        drawable = NULL;
        context = NULL;
    }
}


static void retrace_eglSwapBuffers(trace::Call &call) {
    frame_complete(call);

    if (double_buffer) {
        drawable->swapBuffers();
    } else {
        glFlush();
    }
}

const retrace::Entry glretrace::egl_callbacks[] = {
    {"eglGetError", &retrace::ignore},
    {"eglGetDisplay", &retrace::ignore},
    {"eglInitialize", &retrace::ignore},
    {"eglTerminate", &retrace::ignore},
    {"eglQueryString", &retrace::ignore},
    {"eglGetConfigs", &retrace::ignore},
    {"eglChooseConfig", &retrace::ignore},
    {"eglGetConfigAttrib", &retrace::ignore},
    {"eglCreateWindowSurface", &retrace_eglCreateWindowSurface},
    //{"eglCreatePbufferSurface", &retrace::ignore},
    //{"eglCreatePixmapSurface", &retrace::ignore},
    {"eglDestroySurface", &retrace_eglDestroySurface},
    {"eglQuerySurface", &retrace::ignore},
    {"eglBindAPI", &retrace_eglBindAPI},
    {"eglQueryAPI", &retrace::ignore},
    //{"eglWaitClient", &retrace::ignore},
    //{"eglReleaseThread", &retrace::ignore},
    //{"eglCreatePbufferFromClientBuffer", &retrace::ignore},
    //{"eglSurfaceAttrib", &retrace::ignore},
    //{"eglBindTexImage", &retrace::ignore},
    //{"eglReleaseTexImage", &retrace::ignore},
    {"eglSwapInterval", &retrace::ignore},
    {"eglCreateContext", &retrace_eglCreateContext},
    {"eglDestroyContext", &retrace_eglDestroyContext},
    {"eglMakeCurrent", &retrace_eglMakeCurrent},
    {"eglGetCurrentContext", &retrace::ignore},
    {"eglGetCurrentSurface", &retrace::ignore},
    {"eglGetCurrentDisplay", &retrace::ignore},
    {"eglQueryContext", &retrace::ignore},
    {"eglWaitGL", &retrace::ignore},
    {"eglWaitNative", &retrace::ignore},
    {"eglSwapBuffers", &retrace_eglSwapBuffers},
    //{"eglCopyBuffers", &retrace::ignore},
    {"eglGetProcAddress", &retrace::ignore},
};

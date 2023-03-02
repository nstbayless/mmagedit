#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include <SDL.h>
#include <assert.h>
#include "emu/nes_system.h"

#define TEXTURE_WIDTH   256
#define TEXTURE_HEIGHT  224

#define CONTROLLER_DEADZONE 2048
#define AUDIO_SAMPLES 220 /* 10 ms at 44100 sample rate */

SDL_Rect            video_srcrect = {0,0,TEXTURE_WIDTH, TEXTURE_HEIGHT};
uint32_t*           texture_buffer = 0;
uint32_t            wnd_scale = 3;
SDL_Window*         wnd = 0;
SDL_Renderer*       renderer = 0;
SDL_Texture*        texture = 0;
SDL_GameController* controller[2];
SDL_AudioDeviceID   audio_device_id;

typedef struct ring_buf_t ring_buf_t;
struct ring_buf_t
{
    uint8_t* buffer;
    size_t   write;
    size_t   read;
    size_t   capacity;
};

void ring_buf_write(ring_buf_t* ring, void* data, size_t data_size)
{
    size_t available = ring->read <= ring->write ? (ring->capacity - (ring->write - ring->read)) : (ring->read - ring->write); 
    if (available <= data_size)
    {
        size_t exp = (data_size - available + 1);
        ring->buffer = (uint8_t*)realloc(ring->buffer, ring->capacity + exp);

        if (ring->read > ring->write)
        {
            memmove(ring->buffer + ring->read + exp, ring->buffer + ring->read, ring->capacity - ring->read); 
            ring->read += exp;
        }

        ring->capacity += exp; 
    }

    size_t wrap_size = ring->capacity - ring->write;

    if (data_size <= wrap_size)
    {
        memcpy(ring->buffer + ring->write, data, data_size);
    }
    else
    {
        memcpy(ring->buffer + ring->write, data, wrap_size);
        memcpy(ring->buffer, data + wrap_size, data_size - wrap_size);
    }

    ring->write = (ring->write + data_size) % ring->capacity;
}

size_t ring_buf_available(ring_buf_t* ring)
{
    return ring->read <= ring->write ? (ring->write - ring->read) : (ring->capacity - (ring->read - ring->write));
}

size_t ring_buf_read(ring_buf_t* ring, void* dst, size_t dst_size)
{
    size_t available = ring_buf_available(ring);
    size_t to_read = dst_size < available ? dst_size : available;
    size_t wrap_size = ring->capacity - ring->read;

    if (to_read < wrap_size)
    {
        memcpy(dst, ring->buffer + ring->read, to_read);
    }
    else
    {
        memcpy(dst, ring->buffer + ring->read, wrap_size);
        memcpy(dst + wrap_size, ring->buffer, to_read - wrap_size);
    }

    ring->read = (ring->read + to_read) % ring->capacity;
    return to_read;
}


nes_controller_state on_nes_input(int controller_id, void* client)
{
    nes_controller_state state;
    if (controller_id == 0)
    {
        const uint8_t* keys = SDL_GetKeyboardState(0);
        state.up    = keys[SDL_SCANCODE_W];
        state.down  = keys[SDL_SCANCODE_S];
        state.left  = keys[SDL_SCANCODE_A];
        state.right = keys[SDL_SCANCODE_D];
        state.A     = keys[SDL_SCANCODE_J];
        state.B     = keys[SDL_SCANCODE_K];
        state.select = keys[SDL_SCANCODE_TAB];
        state.start  = keys[SDL_SCANCODE_RETURN];

        if (controller[0])
        {
            state.up     |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_DPAD_UP); 
            state.down   |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_DPAD_DOWN); 
            state.left   |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_DPAD_LEFT); 
            state.right  |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_DPAD_RIGHT); 
            state.A      |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_A); 
            state.B      |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_B); 
            state.select |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_BACK); 
            state.start  |= SDL_GameControllerGetButton(controller[0], SDL_CONTROLLER_BUTTON_START); 

            state.left  |= SDL_GameControllerGetAxis(controller[0], SDL_CONTROLLER_AXIS_LEFTX) < -CONTROLLER_DEADZONE;
            state.right |= SDL_GameControllerGetAxis(controller[0], SDL_CONTROLLER_AXIS_LEFTX) > CONTROLLER_DEADZONE;
            state.up    |= SDL_GameControllerGetAxis(controller[0], SDL_CONTROLLER_AXIS_LEFTY) < -CONTROLLER_DEADZONE;
            state.down  |= SDL_GameControllerGetAxis(controller[0], SDL_CONTROLLER_AXIS_LEFTY) > CONTROLLER_DEADZONE;
        }
        return state;
    }
    else
    {
        memset(&state, 0, sizeof(nes_controller_state));
        return state;
    }
}

void on_nes_video(nes_video_output* video, void* client)
{
    const uint32_t colors[] = {
    0x545454, 0x741E00, 0x901008, 0x880030, 0x640044, 0x30005C, 0x000454, 0x00183C, 0x002A20, 0x003A08, 0x004000, 0x003C00, 0x3C3200, 0x000000, 0, 0,
    0x989698, 0xC44C08, 0xEC3230, 0xE41E5C, 0xB01488, 0x6414A0, 0x202298, 0x003C78, 0x005A54, 0x007228, 0x007C08, 0x287600, 0x786600, 0x000000, 0, 0,
    0xECEEEC, 0xEC9A4C, 0xEC7C78, 0xEC62B0, 0xEC54E4, 0xB458EC, 0x646AEC, 0x2088D4, 0x00AAA0, 0x00C474, 0x20D04C, 0x6CCC38, 0xCCB438, 0x3C3C3C, 0, 0, 
    0xECEEEC, 0xECCCA8, 0xECBCBC, 0xECB2D4, 0xECAEEC, 0xD4AEEC, 0xB0B4EC, 0x90C4E4, 0x78D2CC, 0x78DEB4, 0x90E2A8, 0xB4E298, 0xE4D6A0, 0xA0A2A0, 0, 0};
 
    nes_pixel* pixel = video->framebuffer;
    for (int y = 0; y < video->height; ++y)
    {
        for (int x = 0; x < video->width; ++x)
        {
            texture_buffer[y * 256 + x] = colors[(pixel + x)->value] | 0xFF000000;
        }
        pixel += NES_FRAMEBUFFER_ROW_STRIDE;
    }

    SDL_UpdateTexture(texture, 0, texture_buffer, sizeof(uint32_t) * TEXTURE_WIDTH);
    video_srcrect.w = video->width;
    video_srcrect.h = video->height;
}

ring_buf_t audio_ring_buf;

void init_audio_ring_buf()
{
    audio_ring_buf.buffer = malloc(1024);
    audio_ring_buf.capacity = 1024;
    audio_ring_buf.write = audio_ring_buf.read = 0;
}

float audio_counter = 0.0f;
float latency_avg = 0.0f;

void on_nes_audio(nes_audio_output* audio, void* client)
{
    int16_t resample_buf[512];
    uint32_t dst = 0;

    SDL_LockAudioDevice(audio_device_id);

    const float target_latency = 50.f;
    float increment_rate = 44100.0f / (float)audio->sample_rate;

    float diff = fabsf(target_latency - latency_avg);
    if (diff > 3.0f)
    {
        if (latency_avg < target_latency)
            increment_rate += diff / 44100.0f;
        else
            increment_rate -= diff / 44100.0f;
    }

    for (uint32_t src = 0; src < audio->sample_count; ++src)
    {
        if (audio_counter >= 1.0f)
        {
            audio_counter -= 1.0f;
            resample_buf[dst++] = audio->samples[src];
        }
        audio_counter += increment_rate;

        if (dst == 512)
        {
            ring_buf_write(&audio_ring_buf, resample_buf, dst * sizeof(int16_t));
            dst = 0;
        }
    }

    if (dst)
        ring_buf_write(&audio_ring_buf, resample_buf, dst * sizeof(int16_t));

    SDL_UnlockAudioDevice(audio_device_id);
}

void sdl_audio_callback(void* client, uint8_t* stream, int len)
{
    float latency = ((ring_buf_available(&audio_ring_buf) / sizeof(int16_t)) / 44100.0f) * 1000.0f;
    latency_avg = (latency_avg * 0.99 + latency * 0.01);

    //printf("read latency: %.2f ms  avg: %.2f ms\n", latency, latency_avg);

    int available = ring_buf_available(&audio_ring_buf);
    if (available >= len)
    {
        size_t read = ring_buf_read(&audio_ring_buf, stream, len);
        if (read < len)
            memset(stream + read, 0, len - read);
    }
    else
    {
        memset(stream, 0, len);
    }
}

void handle_shortcut_key(SDL_Scancode key)
{
    const uint8_t* keys = SDL_GetKeyboardState(0);
    int is_ctrl_down = keys[SDL_SCANCODE_LCTRL] | keys[SDL_SCANCODE_RCTRL];
    if (is_ctrl_down)
    {
        int scale = wnd_scale;
        if (key == SDL_SCANCODE_EQUALS) wnd_scale++;
        else if(key == SDL_SCANCODE_MINUS) wnd_scale--;

        if (scale != wnd_scale)
        {
            SDL_SetWindowSize(wnd, TEXTURE_WIDTH * wnd_scale, TEXTURE_HEIGHT * wnd_scale);
        }
    }
}

void handle_joystick_added(uint32_t index)
{
    if (index < 2 && !controller[index] && SDL_IsGameController(index))
    {
        controller[index] = SDL_GameControllerOpen(index);
    }
}

void handle_joystick_removed(uint32_t index)
{
    if (index < 2 && controller[index])
    {
        SDL_GameControllerClose(controller[index]);
        controller[index] = 0;
    }
}

int main(int argc, char** argv)
{
    const char*     rom_path = argc > 1 ? argv[1] : "rom.nes";
    char            title[256];
    int             quit = 0;
    nes_config      config;
    nes_system*     system = 0;
    SDL_AudioSpec   audio_spec_desired, audio_spec_obtained;

    init_audio_ring_buf();

    snprintf(title, 256, "NESM - %s", rom_path);

    config.client_data = 0;
    config.input_callback = &on_nes_input;
    config.video_callback = &on_nes_video;
    config.audio_callback = &on_nes_audio;

    system = nes_system_create(rom_path, &config);
    if (!system)
    {
        fprintf(stderr, "Failed to initialized nes system.\n");
        return -1;
    }

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_JOYSTICK) < 0)
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Failed to initialized SDL2: %s\n", SDL_GetError());
        return -1;
    }

    wnd = SDL_CreateWindow(title, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, 
            TEXTURE_WIDTH * wnd_scale, TEXTURE_HEIGHT * wnd_scale, SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIDDEN);
    if (!wnd)
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Failed to create window: %s\n", SDL_GetError());
        return -1;
    }

    renderer = SDL_CreateRenderer(wnd, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!renderer)
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Failed to create renderer: %s\n", SDL_GetError());
        return -1;
    }

    memset(&audio_spec_desired, 0, sizeof(SDL_AudioSpec));
    audio_spec_desired.freq = 44100;
    audio_spec_desired.channels = 1;
    audio_spec_desired.format = AUDIO_S16;
    audio_spec_desired.samples = AUDIO_SAMPLES;
    audio_spec_desired.callback = sdl_audio_callback;
    audio_device_id = SDL_OpenAudioDevice(0, 0, &audio_spec_desired, &audio_spec_obtained, 0);
    if (audio_device_id < 0)
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION, "Failed to open audio device: %s\n", SDL_GetError());
    }
    SDL_PauseAudioDevice(audio_device_id, 0);

    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "1");
    texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ABGR8888, SDL_TEXTUREACCESS_STREAMING, TEXTURE_WIDTH, TEXTURE_HEIGHT);
    if (!texture)
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Failed to create texture: %s\n", SDL_GetError());
        return -1;
    }

    texture_buffer = (uint32_t*)malloc(TEXTURE_WIDTH * TEXTURE_HEIGHT * sizeof(uint32_t));

    memset(&controller, 0, 2 * sizeof(SDL_GameController*));

    SDL_ShowWindow(wnd);

    while(!quit)
    {
        uint64_t begin_frame = SDL_GetPerformanceCounter();

        int w, h, has_key_up = 0;
        SDL_Scancode key_up_scancode = 0;
        SDL_Rect dstrect;
        SDL_Event evt;
        float aspect_ratio = (float)video_srcrect.w / (float)video_srcrect.h;

        while (SDL_PollEvent(&evt))
        {
            if (evt.type == SDL_QUIT) quit = 1;
            else if (evt.type == SDL_KEYUP)
            {
                has_key_up = 1;
                key_up_scancode = evt.key.keysym.scancode;
            }
            else if (evt.type == SDL_JOYDEVICEADDED)
            {
                handle_joystick_added(evt.jdevice.which);
            }
            else if (evt.type == SDL_JOYDEVICEREMOVED)
            {
                handle_joystick_removed(evt.jdevice.which);
            }
        }

        if (has_key_up)
            handle_shortcut_key(key_up_scancode);

        SDL_GetWindowSize(wnd, &w, &h);
        if (((float)w / (float)h) >= aspect_ratio)
        {
            dstrect.y = 0;
            dstrect.h = h;
            dstrect.w = (float)h * aspect_ratio;
            dstrect.x = (w - dstrect.w)>>1;
        }
        else
        {
            dstrect.x = 0;
            dstrect.w = w;
            dstrect.h = (float)w / aspect_ratio;
            dstrect.y = (h - dstrect.h)>>1;
        }

        nes_system_frame(system);

        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0);
        SDL_RenderClear(renderer);
        SDL_RenderCopy(renderer, texture, &video_srcrect, &dstrect);
        SDL_RenderPresent(renderer);

        uint64_t frame_time = 0;
        while(frame_time < 1666)
        {
           frame_time  = ((SDL_GetPerformanceCounter() - begin_frame)*100000)/SDL_GetPerformanceFrequency();
           if (frame_time < 1666 && (1666 - frame_time) > 100)
               SDL_Delay(1);
        }
    }

    SDL_DestroyWindow(wnd);
    if (audio_device_id >= 0)
        SDL_CloseAudioDevice(audio_device_id);

    nes_system_destroy(system);
    free(texture_buffer);
    free(audio_ring_buf.buffer);

    if (controller[0]) SDL_GameControllerClose(controller[0]);
    if (controller[1]) SDL_GameControllerClose(controller[1]);

    SDL_Quit();
    return 0;
}

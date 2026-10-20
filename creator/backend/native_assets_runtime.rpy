
init 999 python:
    import io as _ca_io
    import struct as _ca_struct
    import threading as _ca_threading
    import zlib as _ca_zlib

    def _ca_safe_path(value):
        return isinstance(value, str) and value and not value.startswith(('/', '\\')) and ':' not in value and '\\' not in value and all(p not in ('', '.', '..') for p in value.split('/'))

    def _ca_silence():
        frames = b'\0\0' * 22050
        return _ca_io.BytesIO(b'RIFF' + _ca_struct.pack('<I', 36 + len(frames)) + b'WAVEfmt ' + _ca_struct.pack('<IHHIIHH', 16, 1, 1, 22050, 44100, 2, 16) + b'data' + _ca_struct.pack('<I', len(frames)) + frames)

    def _ca_blank():
        def chunk(kind, data):
            return _ca_struct.pack('>I', len(data)) + kind + data + _ca_struct.pack('>I', _ca_zlib.crc32(kind + data) & 0xffffffff)
        return _ca_io.BytesIO(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', _ca_struct.pack('>IIBBBBB', 64, 64, 8, 6, 0, 0, 0)) + chunk(b'IDAT', _ca_zlib.compress((b'\0' + b'\x32\x48\x55\xff' * 64) * 64)) + chunk(b'IEND', b''))

    def _ca_placeholder(entry):
        name = entry.get('requirement') or entry['name']
        size = (480, 900) if entry['type'] == 'sprite' else (config.screen_width, config.screen_height) if entry['type'] == 'background' else (600, 600)
        return Composite(size, (0, 0), Solid('#263e49'), (24, 24), Text('素材待补\n' + name, size=28, color='#ffffff', xmaximum=size[0] - 48))

    def _ca_install():
        global _ca_path_bindings, _ca_original_open, _ca_original_loadable, _ca_guard, _ca_gaps
        entries = _creator_asset_table['entries']
        original_images = {e['runtime']['key']: renpy.get_registered_image(e['runtime']['key']) for e in entries if e['runtime']['kind'] == 'image'}
        for e in entries:
            binding = e.get('binding')
            if binding and binding['kind'] in ('label', 'original') and binding['key'] not in original_images:
                original_images[binding['key']] = renpy.get_registered_image(binding['key'])
        _ca_original_open = config.file_open_callback
        _ca_original_loadable = config.loadable_callback
        _ca_guard = _ca_threading.local()
        _ca_path_bindings = {}
        _ca_gaps = []
        # Targets are resolved against original definitions, never other bindings.
        for e in entries:
            kind, key = e['runtime']['kind'], e['runtime']['key']
            binding = e.get('binding')
            baseline_key = e.get('originalPath') if kind == 'audio-variable' else key
            expected = {'kind': 'original' if kind == 'image' else 'file', 'key': baseline_key}
            overridden = e.get('override') or binding != expected
            available = True
            if binding is None:
                available = False
            elif binding['kind'] == 'file':
                available = _ca_safe_path(binding['key']) and renpy.loadable(binding['key'])
            else:
                available = original_images.get(binding['key']) is not None
                if available and binding['kind'] == 'original' and e.get('originalPath'):
                    available = renpy.loadable(e['originalPath'])
                if available and binding['kind'] == 'label' and e.get('targetPath'):
                    available = renpy.loadable(e['targetPath'])
            if kind == 'audio-variable':
                virtual = '_creator_virtual/audio/' + e['id'] + '.wav'
                _ca_path_bindings[virtual.casefold()] = {'path': binding['key'] if available and binding else None, 'audio': True, 'name': e.get('requirement') or e['name'], 'temporary': e.get('temporary', False)}
            if not overridden and available:
                continue
            if kind == 'image':
                target = _ca_placeholder(e)
                if available:
                    target = original_images[binding['key']] if binding['kind'] != 'file' else Image(binding['key'])
                renpy.image(key, target)
            else:
                virtual = '_creator_virtual/audio/' + e['id'] + '.wav' if kind == 'audio-variable' else key
                if kind == 'audio-variable':
                    setattr(renpy.store.audio, key.split('.', 1)[1], virtual)
                _ca_path_bindings[virtual.casefold()] = {'path': binding['key'] if available and binding else None, 'audio': e['type'] in ('bgm', 'ambience', 'sound', 'voice'), 'name': e.get('requirement') or e['name'], 'temporary': e.get('temporary', False)}
        if _ca_path_bindings:
            config.file_open_callback = _ca_open
            config.loadable_callback = _ca_loadable
        if _ca_path_bindings and 'creator_asset_gaps' not in config.overlay_screens:
            config.overlay_screens.append('creator_asset_gaps')

    def _ca_open(name):
        if getattr(_ca_guard, 'active', False):
            return _ca_original_open(name) if _ca_original_open else None
        binding = _ca_path_bindings.get(name.casefold())
        if binding is None:
            return _ca_original_open(name) if _ca_original_open else None
        target = binding['path']
        if (not target or binding['temporary']) and binding['name'] not in _ca_gaps:
            _ca_gaps.append(binding['name'])
        if target:
            _ca_guard.active = True
            try:
                return renpy.file(target)
            except IOError:
                pass
            finally:
                _ca_guard.active = False
        return _ca_silence() if binding['audio'] else _ca_blank()

    def _ca_loadable(name):
        if not getattr(_ca_guard, 'active', False) and name.casefold() in _ca_path_bindings:
            return True
        return bool(_ca_original_loadable(name)) if _ca_original_loadable else False

    # The pinned SDK invokes this after image init statements, still in init.
    renpy.game.post_init.append(_ca_install)

screen creator_asset_gaps():
    zorder 190
    if _ca_gaps:
        frame:
            xalign .5
            ypos 6
            xmaximum config.screen_width - 32
            background Solid('#14222be8')
            padding (12, 6)
            text ('素材待补 · ' + ' ／ '.join(_ca_gaps)) size 18 color '#ffd78c'

import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

// ─── SpaceDefinition ──────────────────────────────────────────────────────────

class SpaceDefinition {
    constructor({ id, name, color = '#a78bfa', appIds = [], lastActive = null }) {
        this.id = id;
        this.name = name;
        this.color = color;
        this.appIds = appIds;
        this.lastActive = lastActive;
    }

    toJSON() {
        return {
            id: this.id,
            name: this.name,
            color: this.color,
            appIds: this.appIds,
            lastActive: this.lastActive,
        };
    }
}

// ─── SpaceIndicator ───────────────────────────────────────────────────────────

const SpaceIndicator = GObject.registerClass(
class SpaceIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Axon Space Indicator', false);

        this._extension = extension;

        const box = new St.BoxLayout({
            style_class: 'axon-space-indicator',
            vertical: false,
            x_align: Clutter.ActorAlign.CENTER,
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._dot = new St.Label({
            style_class: 'axon-space-dot',
            text: '●',
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._label = new St.Label({
            style_class: 'axon-space-label',
            text: 'Space',
            y_align: Clutter.ActorAlign.CENTER,
        });

        box.add_child(this._dot);
        box.add_child(this._label);
        this.add_child(box);
    }

    update(space) {
        if (!space) return;
        this._label.set_text(space.name);
        this._dot.set_style(`color: ${space.color};`);
    }
});

// ─── SpacesManager ────────────────────────────────────────────────────────────

export default class SpacesManager {
    constructor(extension) {
        this._extension = extension;
        this._spaces = [];
        this._currentIndex = 0;
        this._indicator = null;
        this._workspaceChangedId = null;
        this._stateDir = GLib.build_filenamev([GLib.get_home_dir(), '.axon']);
        this._stateFile = GLib.build_filenamev([this._stateDir, 'spaces.json']);
    }

    enable() {
        this._ensureStateDir();
        this._loadState();

        this._indicator = new SpaceIndicator(this._extension);
        Main.panel.addToStatusArea('axon-space-indicator', this._indicator, 0, 'left');
        this._updateIndicator();

        this._workspaceChangedId = global.workspace_manager.connect(
            'active-workspace-changed',
            this._onWorkspaceChanged.bind(this)
        );
    }

    disable() {
        if (this._workspaceChangedId) {
            global.workspace_manager.disconnect(this._workspaceChangedId);
            this._workspaceChangedId = null;
        }

        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }

        this._saveState();
    }

    // ── State persistence ──────────────────────────────────────────────────────

    _ensureStateDir() {
        try {
            const dir = Gio.File.new_for_path(this._stateDir);
            if (!dir.query_exists(null)) {
                dir.make_directory_with_parents(null);
            }
        } catch (e) {
            logError(e, 'AxonShell: could not create ~/.axon directory');
        }
    }

    _loadState() {
        try {
            const file = Gio.File.new_for_path(this._stateFile);
            if (!file.query_exists(null)) {
                this._createDefaultState();
                return;
            }

            const [ok, contents] = file.load_contents(null);
            if (!ok) {
                this._createDefaultState();
                return;
            }

            const decoder = new TextDecoder('utf-8');
            const json = JSON.parse(decoder.decode(contents));

            if (Array.isArray(json.spaces) && json.spaces.length > 0) {
                this._spaces = json.spaces.map(s => new SpaceDefinition(s));
                this._currentIndex = typeof json.currentIndex === 'number'
                    ? Math.min(json.currentIndex, this._spaces.length - 1)
                    : 0;
            } else {
                this._createDefaultState();
            }
        } catch (e) {
            logError(e, 'AxonShell: failed to load spaces state');
            this._createDefaultState();
        }
    }

    _createDefaultState() {
        this._spaces = [
            new SpaceDefinition({
                id: GLib.uuid_string_random(),
                name: 'My Space',
                color: '#a78bfa',
                appIds: [],
                lastActive: null,
            }),
        ];
        this._currentIndex = 0;
        this._saveState();
    }

    saveState() {
        this._saveState();
    }

    _saveState() {
        try {
            const data = {
                currentIndex: this._currentIndex,
                spaces: this._spaces.map(s => s.toJSON()),
            };
            const json = JSON.stringify(data, null, 2);
            const file = Gio.File.new_for_path(this._stateFile);
            const encoder = new TextEncoder();
            const bytes = encoder.encode(json);
            file.replace_contents(
                bytes,
                null,
                false,
                Gio.FileCreateFlags.REPLACE_DESTINATION,
                null
            );
        } catch (e) {
            logError(e, 'AxonShell: failed to save spaces state');
        }
    }

    // ── Workspace / space operations ───────────────────────────────────────────

    switchToSpace(idx) {
        if (idx < 0 || idx >= this._spaces.length) return;

        this._currentIndex = idx;
        this._spaces[idx].lastActive = new Date().toISOString();

        const workspaceManager = global.workspace_manager;
        const nWorkspaces = workspaceManager.get_n_workspaces();

        // Ensure enough workspaces exist
        while (workspaceManager.get_n_workspaces() <= idx) {
            workspaceManager.append_new_workspace(false, global.get_current_time());
        }

        const workspace = workspaceManager.get_workspace_by_index(idx);
        if (workspace) {
            workspace.activate(global.get_current_time());
        }

        this._updateIndicator();
        this._saveState();
    }

    createSpace(name, color = '#a78bfa') {
        const space = new SpaceDefinition({
            id: GLib.uuid_string_random(),
            name,
            color,
            appIds: [],
            lastActive: null,
        });
        this._spaces.push(space);
        this._saveState();
        return space;
    }

    getSpaces() {
        return [...this._spaces];
    }

    getCurrentSpace() {
        return this._spaces[this._currentIndex] || this._spaces[0] || null;
    }

    // ── Internal ───────────────────────────────────────────────────────────────

    _onWorkspaceChanged() {
        const activeIndex = global.workspace_manager.get_active_workspace_index();
        if (activeIndex >= 0 && activeIndex < this._spaces.length) {
            this._currentIndex = activeIndex;
        } else if (activeIndex >= this._spaces.length) {
            // Workspace exists but no corresponding space; use last space
            this._currentIndex = this._spaces.length - 1;
        }
        this._updateIndicator();
    }

    _updateIndicator() {
        if (this._indicator) {
            this._indicator.update(this.getCurrentSpace());
        }
    }
}

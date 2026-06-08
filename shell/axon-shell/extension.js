import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Shell from 'gi://Shell';
import Meta from 'gi://Meta';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';

import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

import SpacesManager from './spaces.js';
import IntentBar from './intentbar.js';

export default class AxonShellExtension extends Extension {
    constructor(metadata) {
        super(metadata);
        this._spacesManager = null;
        this._intentBar = null;
        this._keybindingIds = [];
    }

    enable() {
        this._spacesManager = new SpacesManager(this);
        this._spacesManager.enable();

        this._intentBar = new IntentBar(this, this._spacesManager);
        this._intentBar.enable();

        this._registerKeybindings();
    }

    _registerKeybindings() {
        const settings = this.getSettings();

        // Super+1..9 to switch spaces
        for (let i = 1; i <= 9; i++) {
            const spaceIndex = i - 1;
            const bindingName = `switch-to-space-${i}`;
            try {
                Main.wm.addKeybinding(
                    bindingName,
                    settings,
                    Meta.KeyBindingFlags.NONE,
                    Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW,
                    () => {
                        this._spacesManager.switchToSpace(spaceIndex);
                    }
                );
                this._keybindingIds.push(bindingName);
            } catch (e) {
                // Binding may not exist in schema; skip gracefully
                logError(e, `AxonShell: could not bind ${bindingName}`);
            }
        }

        // Toggle intent bar binding
        try {
            Main.wm.addKeybinding(
                'toggle-intent-bar',
                settings,
                Meta.KeyBindingFlags.NONE,
                Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW,
                () => {
                    this._intentBar.toggle();
                }
            );
            this._keybindingIds.push('toggle-intent-bar');
        } catch (e) {
            logError(e, 'AxonShell: could not bind toggle-intent-bar');
        }
    }

    disable() {
        // Remove all registered keybindings
        for (const id of this._keybindingIds) {
            try {
                Main.wm.removeKeybinding(id);
            } catch (e) {
                logError(e, `AxonShell: could not remove keybinding ${id}`);
            }
        }
        this._keybindingIds = [];

        if (this._intentBar) {
            this._intentBar.disable();
            this._intentBar = null;
        }

        if (this._spacesManager) {
            this._spacesManager.disable();
            this._spacesManager = null;
        }
    }
}

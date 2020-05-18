/* eslint-disable ghost/ember/alias-model-in-controller */
import Controller from '@ember/controller';
import {alias} from '@ember/object/computed';
import {inject as service} from '@ember/service';
import {task, timeout} from 'ember-concurrency';

export default Controller.extend({
    notifications: service(),
    settings: service(),
    intl: service(),

    dirtyAttributes: null,
    rollbackValue: null,
    leaveSettingsTransition: null,

    unsplashSettings: alias('settings.unsplash'),

    actions: {
        save() {
            this.save.perform();
        },

        update(value) {
            if (!this.dirtyAttributes) {
                this.set('rollbackValue', this.get('unsplashSettings.isActive'));
            }
            this.set('unsplashSettings.isActive', value);
            this.set('dirtyAttributes', true);
        },

        toggleLeaveSettingsModal(transition) {
            let leaveTransition = this.leaveSettingsTransition;

            if (!transition && this.showLeaveSettingsModal) {
                this.set('leaveSettingsTransition', null);
                this.set('showLeaveSettingsModal', false);
                return;
            }

            if (!leaveTransition || transition.targetName === leaveTransition.targetName) {
                this.set('leaveSettingsTransition', transition);

                // if a save is running, wait for it to finish then transition
                if (this.get('save.isRunning')) {
                    return this.get('save.last').then(() => {
                        transition.retry();
                    });
                }

                // we genuinely have unsaved data, show the modal
                this.set('showLeaveSettingsModal', true);
            }
        },

        leaveSettings() {
            let transition = this.leaveSettingsTransition;

            if (!transition) {
                this.notifications.showAlert(this.intl.t('Sorry, there was an error in the application. Please let the Ghost team know what happened.'), {type: 'error'});
                return;
            }

            // roll back changes on model props
            this.set('unsplashSettings.isActive', this.rollbackValue);
            this.set('dirtyAttributes', false);
            this.set('rollbackValue', null);

            return transition.retry();
        }
    },

    saveTask: task(function* () {
        let unsplash = this.unsplashSettings;
        let settings = this.settings;

        try {
            settings.set('unsplash', unsplash);
            this.set('dirtyAttributes', false);
            this.set('rollbackValue', null);
            return yield settings.save();
        } catch (error) {
            if (error) {
                this.notifications.showAPIError(error);
                throw error;
            }
        }
    }).drop(),

    save: task(function* () {
        yield this.saveTask.perform();
        yield timeout(2500);
        if (this.get('saveTask.last.isSuccessful') && this.get('saveTask.last.value')) {
            // Reset last task to bring button back to idle state
            yield this.set('saveTask.last', null);
        }
    }).drop()
});

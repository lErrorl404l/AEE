/* SPDX-License-Identifier: GPL-2.0-or-later */
// The dev harness addon. Built by tools/dev-harness/, which sits outside the
// main project's addons/ and optionals/. The main hemtt build and hemtt
// release cannot see this project.
class CfgPatches {
    class aee_dev {
        name = "AEE Dev Harness";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.02;
        requiredAddons[] = {"cba_main", "cba_xeh", "cba_keybinding"};
        author = "lErrorl404l";
        url = "https://github.com/lErrorl404l/AEE";
        version = 1.0;
        versionStr = "1.0.0.0";
        versionAr[] = {1,0,0,0};
    };
};

#include "CfgEventHandlers.hpp"

/* SPDX-License-Identifier: GPL-2.0-or-later */
// TEST ONLY. The land-physics fixture addon for the Docker probe. It declares
// requiredAddons {"aee_mobility"}, so the engine loads it after AEE and the
// class both declare is merged. This addon is built only by tools/docker_test.sh
// and copied into the test @aee. It is never part of a release.
class CfgPatches {
    class probe_physics {
        name = "AEE Land-Physics Fixture Probe";
        units[] = {};
        weapons[] = {};
        requiredVersion = 1.0;
        requiredAddons[] = {"aee_mobility"};
        author = "AEE";
    };
};

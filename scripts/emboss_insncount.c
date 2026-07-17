/* Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Minimal QEMU TCG plugin used by size_bench.py --speed: counts retired guest
 * instructions and prints the total to stderr at exit as `insns: <N>`. The count
 * is deterministic for a given (binary, guest arch), which makes it a stable
 * cross-architecture execution-speed metric where wall-clock is not.
 *
 * It uses an inline per-vCPU add (no per-instruction callback), so emulation runs
 * at near-native qemu speed even for billions of instructions.
 *
 * Built against the QEMU 10.x plugin API (version 4). QEMU's own contrib/plugins
 * no longer ships an instruction counter (libinsn was dropped), hence this local
 * plugin. Build it with scripts/build_qemu_plugin.sh.
 */

#include <inttypes.h>
#include <stddef.h>
#include <stdio.h>

#include <glib.h>
#include <qemu-plugin.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static struct qemu_plugin_scoreboard *score;
static qemu_plugin_u64 insn_count;

static void vcpu_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb) {
  size_t n = qemu_plugin_tb_n_insns(tb);
  for (size_t i = 0; i < n; i++) {
    struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
    qemu_plugin_register_vcpu_insn_exec_inline_per_vcpu(
        insn, QEMU_PLUGIN_INLINE_ADD_U64, insn_count, 1);
  }
}

static void plugin_exit(qemu_plugin_id_t id, void *p) {
  fprintf(stderr, "insns: %" PRIu64 "\n", qemu_plugin_u64_sum(insn_count));
}

QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                           const qemu_info_t *info, int argc,
                                           char **argv) {
  score = qemu_plugin_scoreboard_new(sizeof(uint64_t));
  insn_count = qemu_plugin_scoreboard_u64(score);
  qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
  qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);
  return 0;
}

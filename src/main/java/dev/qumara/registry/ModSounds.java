package dev.qumara.registry;

import dev.qumara.QumaraMod;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.sound.SoundEvent;
import net.minecraft.util.Identifier;

/** Eventos de sonido propios. En sounds.json apuntan a sonidos vanilla (type=event) y se pueden sustituir por .ogg propios. */
public final class ModSounds {
    public static final SoundEvent IDLE = reg("idle");
    public static final SoundEvent SPAWN_RUMBLE = reg("spawn_rumble");
    public static final SoundEvent EARTH_CRACK = reg("earth_crack");
    public static final SoundEvent ROOTS_GROW = reg("roots_grow");
    public static final SoundEvent ARM_MOVE = reg("arm_move");
    public static final SoundEvent TONGUE_LASH = reg("tongue_lash");
    public static final SoundEvent IMPACT = reg("impact");
    public static final SoundEvent WARNING = reg("warning");
    public static final SoundEvent FURY = reg("fury");
    public static final SoundEvent HURT = reg("hurt");
    public static final SoundEvent DEATH = reg("death");
    public static final SoundEvent GARDEN_BLOOM = reg("garden_bloom");
    public static final SoundEvent VINE_WHIP = reg("vine_whip");
    // ---- identidad sonora ampliada: respiracion, lengua, brazo, impactos, plantas, agarre, fases, muerte
    public static final SoundEvent BREATH = reg("breath");
    public static final SoundEvent TONGUE_FLICK = reg("tongue_flick");
    public static final SoundEvent TONGUE_EXTEND = reg("tongue_extend");
    public static final SoundEvent TONGUE_RETRACT = reg("tongue_retract");
    public static final SoundEvent DRAG_SCRAPE = reg("drag_scrape");
    public static final SoundEvent ARM_WHOOSH = reg("arm_whoosh");
    public static final SoundEvent SLAM_HEAVY = reg("slam_heavy");
    public static final SoundEvent ROOT_BURST = reg("root_burst");
    public static final SoundEvent PLANT_GROW = reg("plant_grow");
    public static final SoundEvent GRAB_CATCH = reg("grab_catch");
    public static final SoundEvent SQUEEZE = reg("squeeze");
    public static final SoundEvent PHASE_SHIFT = reg("phase_shift");
    public static final SoundEvent DEATH_ROAR = reg("death_roar");
    public static final SoundEvent VENOM_SPIT = reg("venom_spit");
    public static final SoundEvent STEP_HEAVY = reg("step_heavy");

    private static SoundEvent reg(String name) {
        Identifier id = QumaraMod.id(name);
        return Registry.register(Registries.SOUND_EVENT, id, SoundEvent.of(id));
    }

    public static void init() {}

    private ModSounds() {}
}

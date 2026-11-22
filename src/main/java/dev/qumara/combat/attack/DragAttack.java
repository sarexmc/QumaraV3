package dev.qumara.combat.attack;

import dev.qumara.combat.DangerShape;
import dev.qumara.combat.DangerZone;
import dev.qumara.combat.RootedManager;
import dev.qumara.combat.Scale;
import dev.qumara.entity.QumaraEntity;
import dev.qumara.registry.ModSounds;
import dev.qumara.vfx.Vfx;
import net.minecraft.block.Blocks;
import net.minecraft.entity.LivingEntity;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.util.math.Vec3d;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/**
 * ATAQUE ARRASTRADO. Qumara clava el brazo en la tierra a su derecha y lo ARRASTRA en linea recta por delante de ella, de derecha a
 * izquierda (o de izquierda a derecha en la version 'back', encadenada en furia+). La franja roja es EXACTAMENTE la trayectoria de la
 * palma (tools/anims.py: DRAG_Z, DRAG_X0, DRAG_X1, DRAG_T0, DRAG_T1) y el dano lo causa la propia mano: la posicion de la palma sale de
 * la trayectoria de la animacion (QumaraEntity.handPos), asi que solo golpea a quien esta justo donde el brazo esta en ese instante.
 * Se esquiva saliendo de la franja o saltando (la garra roza el suelo).
 */
public class DragAttack extends BossAttack {
    public static final double Z_BLOCKS = 7.5, X0_RIGHT = 11.0, X1_RIGHT = -2.0;        // = tools/anims.py
    public static final float T0 = 25f, T1 = 51f, TOTAL = 72f;                           // contacto / fin (ticks de animacion; 1.25 s y 2.55 s)
    public static final float HALF = 2.6f;                                               // semiancho de la franja (bloques)
    public static final double REACH_ALONG = 3.2;                                        // la garra cubre +-3.2 bloques alrededor de la palma
    public static final float DAMAGE = 15f;

    private final boolean reverse;
    private DangerZone zone;
    private Vec3d origin, dir; private double length;
    private final Set<UUID> hit = new HashSet<>();
    private double lastSprout = -99;

    public DragAttack() { this(false); }
    public DragAttack(boolean reverse) { this.reverse = reverse; }

    @Override public String animation() { return reverse ? "drag_back" : "drag"; }
    @Override public String tongueAnimation() { return "lengua_rugir"; }
    @Override public float total() { return TOTAL; }

    @Override
    public void start(QumaraEntity b, LivingEntity target) {
        double x0 = reverse ? X1_RIGHT : X0_RIGHT, x1 = reverse ? X0_RIGHT : X1_RIGHT;
        origin = b.getPos().add(b.right().multiply(x0)).add(b.forward().multiply(Z_BLOCKS));
        dir = b.right().multiply(Math.signum(x1 - x0)).normalize();            // hacia la izquierda del jefe (o derecha en 'back')
        length = Math.abs(x1 - x0);
        double y = b.groundY(origin.x, origin.z);
        origin = new Vec3d(origin.x, y, origin.z);
        zone = show(b, new DangerShape.Strip(origin.x, origin.z, (float) dir.x, (float) dir.z, (float) length, HALF), y, T0, (T1 - T0) + 8f, DangerZone.SWEEP);
        b.sound(ModSounds.WARNING, 3.0f, 0.7f);
        b.sound(ModSounds.ARM_WHOOSH, 3.5f, 0.6f);
    }

    @Override
    public void tick(QumaraEntity b, float prev, float now) {
        if (crossed(prev, now, 4f)) b.sound(ModSounds.PLANT_GROW, 2.5f, 0.6f);
        if (crossed(prev, now, T0 - 3f)) b.sound(ModSounds.WARNING, 3.0f, 1.2f);
        if (crossed(prev, now, T0)) {                                          // la garra se clava
            Vec3d h = ground(b, now);
            Vfx.slamImpact(b.sw(), h);
            b.sound(ModSounds.IMPACT, 4.5f, 0.9f); b.heavy(4.5f, 0.9f); b.sound(ModSounds.EARTH_CRACK, 3.5f, 0.8f);
            b.shake(12, 0.5f);
        }
        if (now >= T0 && now <= T1 + 1f) {
            Vec3d h = ground(b, now);
            double along = h.subtract(origin).dotProduct(dir);
            int t = (int) now;
            // surco continuo: tierra, hojas y fragmentos en la punta (cada tick), raices que brotan a su paso
            Vfx.drag(b.sw(), h, dir);
            Vfx.burst(b.sw(), Vfx.DIRT, h.add(dir.multiply(-1.5)).add(0, 0.3, 0), 6, 1.4, 0.12);
            if (t % 5 == 0 && t != (int) prev) Vfx.burst(b.sw(), Vfx.PODZOL, h.add(0, 0.5, 0), 10, 2.0, 0.25);
            if (along - lastSprout >= 2.8 && along <= length) {
                lastSprout = along;
                Vfx.rootEruption(b.sw(), h);
                b.plants().sprout(Blocks.MANGROVE_ROOTS.getDefaultState(), h, 1.1f * Scale.KF, 2.2f * Scale.KF, 0, 0, 0f, 0, 4, 20, 8);
                b.sound(ModSounds.ROOT_BURST, 2.5f, 0.8f + b.rng().nextFloat() * 0.4f);
            }
            if (t != (int) prev && t % 3 == 0) b.sound(ModSounds.DRAG_SCRAPE, 3.5f, 0.7f + b.rng().nextFloat() * 0.3f);
            if (t != (int) prev && t % 8 == 0) b.shake(8, 0.3f);
            // dano: solo donde esta la garra en este instante
            for (ServerPlayerEntity p : b.zones().playersIn(zone)) {
                if (hit.contains(p.getUuid())) continue;
                double ap = p.getPos().subtract(origin).dotProduct(dir);
                if (Math.abs(ap - along) > REACH_ALONG) continue;
                if (p.getY() - b.groundY(p.getX(), p.getZ()) > 1.4) continue;                 // saltar la esquiva
                hit.add(p.getUuid());
                b.hurtPlayer(p, DAMAGE);
                RootedManager.root(p, 14);
                Vec3d push = dir.multiply(1.1);
                p.setVelocity(push.x, 0.55, push.z); p.velocityModified = true;                 // el brazo los arrastra consigo
                Vfx.burst(b.sw(), Vfx.DIRT, p.getPos().add(0, 0.5, 0), 24, 1.0, 0.3);
                b.sound(ModSounds.IMPACT, 3.0f, 1.3f);
            }
        }
        if (crossed(prev, now, T1)) { b.sound(ModSounds.ROOT_BURST, 3.0f, 0.6f); b.sound(ModSounds.STEP_HEAVY, 3.0f, 0.8f); b.shake(10, 0.35f); Vfx.slamImpact(b.sw(), ground(b, now)); }
    }

    private Vec3d ground(QumaraEntity b, float now) {
        Vec3d h = b.handPos(animation(), now);
        if (h == null) h = origin;
        return new Vec3d(h.x, b.groundY(h.x, h.z), h.z);
    }

    /** En furia o ira encadena el arrastre de vuelta (mismo brazo, sentido contrario). */
    @Override
    public BossAttack next(QumaraEntity b) { return (b.fury() && !reverse && b.rng().nextFloat() < 0.75f) ? new DragAttack(true) : null; }
}

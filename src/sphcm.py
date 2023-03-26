### START IMPORTS ###
import math
### END IMPORTS ###

def complex_perm(freq, relperm, cond):
    return (relperm * 8.854 * 10**(-12)) - 1j * cond / (freq * 2.0 * math.pi)

#def CM_equation(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    #return ((complex_perm(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond) - complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond)) / (complex_perm(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond) + 2 * complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond)))

#def complex_perm_maxwell(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
#    return (complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond) * (1 + 3 * 0.3 * (CM_equation(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond)))/(1 - 0.3 * CM_equation(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond)))

def hopa_CMfactor(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    return ((complex_perm(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond) - complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond))/(complex_perm(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond) + 2 * complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond))).real

def hopa_DEPforce(freq, fitting_gen_fieldgrad, fitting_sish_particle_radius, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    return 2.0 * math.pi * (fitting_gen_buffer_perm * 8.854 * 10.0**(-6)) * fitting_sish_particle_radius**3 * hopa_CMfactor(freq, fitting_hopa_particle_perm, fitting_hopa_particle_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond) * fitting_gen_fieldgrad

def model_hopa_CMfactor(frequencyList, ParticlePermitivity, ParticleConductivity, MediumPermitivity, MediumConductivity):
    CMfactorList = []
    for x in frequencyList:
        y = hopa_CMfactor(x, ParticlePermitivity, ParticleConductivity, MediumPermitivity, MediumConductivity)
        CMfactorList.append(y)

    return CMfactorList

def model_hopa_DEPforce(frequencyList, ElectricFieldGrad, ParticleRadius, ParticlePermitivity, ParticleConductivity, MediumPermitivity, MediumConductivity):
    DEPforceList = []
    for x in frequencyList:
        y = hopa_DEPforce(x, ElectricFieldGrad, ParticleRadius, ParticlePermitivity, ParticleConductivity, MediumPermitivity, MediumConductivity)
        DEPforceList.append(y)

    return DEPforceList